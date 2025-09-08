import logging
import time
from typing import Callable, List
from pathlib import Path
import shutil
from filelock import FileLock

from .sheet_client import SheetClient
from .source_manager import SourceManager
from .task_manager import TaskManager
from .config import Config
from .add_sources import import_sources_from_file
from .utils.system_utils import get_machine_hostname

logger = logging.getLogger(__name__)


class Coordinator:
    """
    Manages a distributed task queue using Google Sheets.
    """

    def __init__(self, config: Config):
        """Initializes all necessary management classes."""
        
        self.config = config
        self.client = SheetClient(config)
        self.source_manager = SourceManager(self.client)
        self.task_manager = TaskManager(self.client)
        self.sources_file_path = config.sources_file_path
        self.last_health_check_time = 0
        logger.info("Coordinator initialized.")


    def _perform_health_check(self):
        """
        Updates the worker's status in the spreadsheet to show it's active.
        """
        
        now = time.monotonic()
        if (now - self.last_health_check_time) > self.config.health_check_interval_seconds:
            logger.info("Performing health check...")
            hostname = get_machine_hostname()
            self.client.update_worker_status(hostname, self.config.STATUS_ACTIVE)
            self.last_health_check_time = now


    def _ensure_tasks_are_available(self):
        """
        Checks if there are pending tasks and attempts to expand sources if none are found.
        """
        
        if not self.client.find_next_pending_task():
            logger.info("No pending video tasks found. Checking for new sources to expand...")
            self._run_source_expansion_phase()


    def _import_sources(self):
        """Imports new sources from the file specified in the configuration."""
        
        if not self.sources_file_path:
            logger.info("No source file path provided. Skipping import.")
            return

        logger.info("Attempting to import new sources from %s", self.sources_file_path)
        import_sources_from_file(self.sources_file_path, self.client)


    def _run_source_expansion_phase(self):
        """
        Finds a new source and orchestrates the expansion and task creation process.
        If no source is found, attempts to import new ones.
        """

        source = self.source_manager.get_next_source_to_expand()

        if not source:
            logger.info("No pending sources available. Checking file for new imports...")
            self._import_sources()
            source = self.source_manager.get_next_source_to_expand()

        if not source:
            logger.warning("Still no pending sources to expand after import attempt.")
            return

        logger.info(f"Processing source expansion for ID: {source.id} | URL: {source.url}")
        self.source_manager.process_source_expansion(source)
        

    def process_next_task(self, processing_function: Callable[[str], None]) -> bool:
        """
        Claims the next available task and executes the processing function.

        Args:
            processing_function (Callable[[str], None]): A function that processes the task's URL.

        Returns:
            bool: True if a task was successfully processed, False if no tasks were available.
        """
        
        self._perform_health_check()
        self._ensure_tasks_are_available()

        logger.info("--- Attempting to claim a video task ---")
        task = self.task_manager.get_next_task()

        if not task:
            logger.info("No pending video tasks available at the moment.")
            return False

        try:
            logger.info("Delivering task ID: %s | URL: %s", task.id, task.url)
            processing_function(task.url)
            logger.info("Processing function successfully completed for task ID %s.", task.id)
            self.task_manager.mark_task_as_done(task)

        except Exception as e:
            logger.exception("Processing function failed for task ID %s.", task.id)
            self.task_manager.mark_task_as_error(task, str(e))

        return True


    def _get_result_folders_by_source_id(self, source_id: str) -> List[Path]:
        """
        Fetches the results for a given source ID by listing the corresponding
        directories in the results directory.
        """

        logger.info(f"Fetching results for source ID: {source_id}")
        tasks = self.client.get_tasks_by_source_id(source_id)
        
        done_tasks = [
            task for task in tasks 
            if task.get('Status') == self.config.STATUS_DONE and task.get('ClaimedBy') == get_machine_hostname()
        ]

        results_path = Path(self.config.results_dir)
        results_path.mkdir(exist_ok=True)

        result_folders = []
        for task in done_tasks:
            task_id = str(task.get('ID'))
            task_folder = results_path / task_id
            if task_folder.is_dir():
                result_folders.append(task_folder)
        
        logger.info(f"Found {len(result_folders)} result folders for source ID {source_id} on this machine.")
        return result_folders


    def manage_results(self, source_id: str = None):
        """
        Atomically moves result folders to a destination directory and back.
        """

        dest_path = Path(self.config.selected_dir)
        dest_path.mkdir(exist_ok=True)

        results_path = Path(self.config.results_dir)
        lock_path = Path(".results.lock")

        with FileLock(lock_path):
            for item in dest_path.iterdir():
                if item.is_dir():
                    shutil.move(str(item), str(results_path / item.name))
                    logger.info(f"Moved back {item.name} to results.")

            if source_id:
                folders_to_move = self._get_result_folders_by_source_id(source_id)

                for folder in folders_to_move:
                    shutil.move(str(folder), str(dest_path / folder.name))
                    logger.info(f"Moved {folder.name} to {dest_path}.")