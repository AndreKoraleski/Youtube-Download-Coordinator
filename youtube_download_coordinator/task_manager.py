import logging
import random
import time
from typing import Dict, Union

from .sheet_client import SheetClient
from .video_task import VideoTask
from .utils.time_utils import get_current_timestamp
from .utils.system_utils import get_machine_hostname


logger = logging.getLogger(__name__)


class TaskManager:
    """
    Manages the process of claiming and updating individual video tasks on the spreadsheet.
    
    This class provides a simple public interface for external scripts to get a
    task to download and mark it as completed or failed.
    """
    
    def __init__(self, sheet_client: SheetClient):
        """
        Initializes the TaskManager with a SheetClient instance.
        """
        
        self.client = sheet_client


    def get_next_task(self) -> Union[VideoTask, None]:
        """
        Claims the next available video task from the spreadsheet.

        This method implements a claim-and-verify pattern to ensure only one
        machine can work on a task at a time. It also handles stalled tasks.
        """

        time.sleep(random.uniform(0, self.client.config.claim_jitter_seconds))

        stalled_task_data = self._find_stalled_task()
        
        if stalled_task_data:
            new_retry_count = int(stalled_task_data.get('RetryCount', 0)) + 1
            if new_retry_count > self.client.config.max_retries:
                self.client.move_task_to_dead_letter(
                    row_id=str(stalled_task_data.get('ID')),
                    error_message="Task stalled after maximum retries."
                )
            else:
                self.client.update_row(
                    worksheet=self.client.video_tasks_worksheet,
                    row_id=str(stalled_task_data.get('ID')),
                    updates={
                        'Status': self.client.config.STATUS_PENDING,
                        'RetryCount': new_retry_count
                    }
                )
                logger.info(f"Reset stalled task with ID {stalled_task_data.get('ID')} to 'pending'.")
                time.sleep(self.client.config.api_wait_seconds)

        task_data = self.client.find_next_pending_task()
        if not task_data:
            logger.info("No pending video tasks found.")
            return None

        task_id = str(task_data.get('ID'))
        hostname = get_machine_hostname()
        timestamp = get_current_timestamp()

        try:
            self.client.update_row(
                worksheet=self.client.video_tasks_worksheet,
                row_id=str(task_id),
                updates={
                    'Status': self.client.config.STATUS_IN_PROGRESS,
                    'ClaimedBy': hostname,
                    'ClaimedAt': timestamp
                }
            )

            re_read_task = self.client._get_task_by_id(str(task_id))

            if re_read_task and re_read_task.get('ClaimedBy') == hostname:
                logger.info(f"Successfully claimed task ID {task_id}.")
                return VideoTask.from_dict(re_read_task)
            
            else:
                logger.warning(f"Failed to claim task ID {task_id}. Another machine claimed it first.")
                return None

        except Exception as e:
            logger.error(f"Error while claiming task ID {task_id}: {e}")
            return None
    

    def _find_stalled_task(self) -> Union[Dict, None]:
        """
        Scans the video tasks sheet for any 'in-progress' tasks that have timed out.
        """

        records = self.client.get_video_tasks()
        current_time_epoch = time.time()
        timeout_seconds = self.client.config.stalled_task_timeout_minutes * 60

        for record in records:
            if record.get('Status') == self.client.config.STATUS_IN_PROGRESS:
                claimed_at_str = record.get('ClaimedAt')
                if claimed_at_str:
                    claimed_at_epoch = time.mktime(time.strptime(claimed_at_str, "%Y-%m-%d %H:%M:%S"))
                    if (current_time_epoch - claimed_at_epoch) > timeout_seconds:
                        return record
        return None
    

    def mark_task_as_done(self, task: VideoTask):
        """
        Updates the status of a video task to 'Done' after successful processing.
        """

        try:
            self.client.update_row(
                worksheet=self.client.video_tasks_worksheet,
                row_id=str(task.id),
                updates={'Status': self.client.config.STATUS_DONE}
            )
            logger.info(f"Task ID {task.id} marked as 'Done'.")

        except Exception as e:
            logger.error(f"Failed to mark task ID {task.id} as done: {e}")


    def mark_task_as_error(self, task: VideoTask, error_message: str = ""):
        """
        Updates the status of a video task to 'Error' if processing fails.

        If the task's retry count exceeds the maximum, it moves the task to the
        dead-letter queue. Otherwise, it increments the retry count and resets
        the status to 'pending'.
        """

        is_fatal = any(sub in error_message for sub in self.client.config.fatal_error_substrings)

        if task.retry_count >= self.client.config.max_retries or is_fatal:
            try:
                self.client.move_task_to_dead_letter(str(task.id), error_message)

            except Exception as e:
                logger.error(f"Failed to move task ID {task.id} to the dead-letter queue: {e}")

        else:
            try:
                new_retry_count = task.retry_count + 1
                self.client.update_row(
                    worksheet=self.client.video_tasks_worksheet,
                    row_id=str(task.id),
                    updates={
                        'Status': self.client.config.STATUS_PENDING,
                        'RetryCount': new_retry_count,
                        'LastError': error_message
                    }
                )
                logger.info(f"Task ID {task.id} failed. Reset to 'pending' with retry count {new_retry_count}.")

            except Exception as e:
                logger.error(f"Failed to mark task ID {task.id} as error: {e}")