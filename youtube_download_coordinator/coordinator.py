import logging
from typing import Callable

from .sheet_client import SheetClient
from .source_manager import SourceManager
from .task_manager import TaskManager
from .config import Config
from .add_sources import import_sources_from_file


logger = logging.getLogger(__name__)


class Coordinator:
    """
    Manages a distributed task queue using Google Sheets.
    """

    def __init__(self, config: Config):
        """Initializes all necessary management classes."""
        
        self.client = SheetClient(config)
        self.source_manager = SourceManager(self.client)
        self.task_manager = TaskManager(self.client)
        self.sources_file_path = config.sources_file_path
        logger.info("Coordinator initialized.")


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
        Finds a new source, expands it, and adds tasks to the sheet.
        If no source is found, attempts to import new ones.
        """
        
        source = self.source_manager.get_next_source_to_expand()

        if not source:
            logger.info("No pending sources available to expand. Checking file for import...")
            self._import_sources()
            source = self.source_manager.get_next_source_to_expand()

        if not source:
            logger.warning("Still no pending sources to expand after import attempt.")
            return

        try:
            logger.info("Expanding source ID: %s | URL: %s", source.id, source.url)
            video_tasks = self.source_manager.expand_source(source)

            if not video_tasks:
                logger.info("Source expansion did not result in video tasks. Marking as done.")
                self.source_manager.mark_source_as_done(str(source.id))
                return

            logger.info("Adding %d new video tasks to the sheet.", len(video_tasks))
            self.source_manager.add_video_tasks_to_sheet(video_tasks)
            self.source_manager.mark_source_as_done(str(source.id))
            logger.info("Source ID %s processed successfully.", source.id)

        except Exception:
            logger.exception("Error during source expansion for source ID %s.", source.id)
            self.source_manager.mark_source_as_error(str(source.id))


    def process_next_task(self, processing_function: Callable[[str], None]) -> bool:
        """
        Claims the next available task and executes the processing function.

        Args:
            processing_function (Callable[[str], None]): A function that processes the task's URL.

        Returns:
            bool: True if a task was successfully processed, False if no tasks were available.
        """
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
            
        except Exception:
            logger.exception("Processing function failed for task ID %s.", task.id)
            self.task_manager.mark_task_as_error(task)

        return True