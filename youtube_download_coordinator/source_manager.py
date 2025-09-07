import logging
import random
import time
from typing import Dict, List, Union

import yt_dlp

from .sheet_client import SheetClient
from .source import Source
from .video_task import VideoTask
from .utils.time_utils import get_current_timestamp
from .utils.system_utils import get_machine_hostname


logger = logging.getLogger(__name__)


class SourceManager:
    """
    Manages the process of expanding a YouTube source (playlist or channel)
    into individual video tasks on the spreadsheet.
    """

    def __init__(self, sheet_client: SheetClient):
        """
        Initializes the SourceManager with a SheetClient instance.
        """
        
        self.client = sheet_client

    def get_next_source_to_expand(self) -> Union[Source, None]:
        """
        Claims the next pending source from the spreadsheet for expansion.

        This method implements a claim-and-verify pattern to prevent race
        conditions in a distributed environment.
        """

        time.sleep(random.uniform(0, self.client.config.claim_jitter_seconds))

        stalled_source_data = self._find_stalled_source()
        
        if stalled_source_data:
            self.client.update_row(
            worksheet=self.client.sources_worksheet,
            row_id=str(stalled_source_data.get('ID')),
            updates={'Status': self.client.config.STATUS_PENDING, 'ClaimedBy': None, 'ClaimedAt': None, 'RetryCount': int(stalled_source_data.get('RetryCount', 0)) + 1}
            )

            logger.info(f"Reset stalled source with ID {stalled_source_data.get('ID')} to 'pending'.")
            time.sleep(self.client.config.api_wait_seconds)

        source_data = self.client.find_next_pending_source()

        if not source_data:
            return None
        
        source_id = str(source_data.get('ID'))
        hostname = get_machine_hostname()
        timestamp = get_current_timestamp()

        try:
            self.client.update_row(
                worksheet=self.client.sources_worksheet,
                row_id=str(source_id),
                updates={
                    'Status': self.client.config.STATUS_IN_PROGRESS,
                    'ClaimedBy': hostname,
                    'ClaimedAt': timestamp
                }
            )

            re_read_source = self.client._get_source_by_id(str(source_id))

            if re_read_source and re_read_source.get('ClaimedBy') == hostname:
                logger.info(f"Successfully claimed source ID {source_id}.")
                return Source.from_dict(re_read_source)
            else:
                logger.warning(f"Failed to claim source ID {source_id}. Another machine claimed it first.")
                return None
        
        except Exception as e:
            logger.error(f"Failed to claim source ID {source_id}: {e}")
            return None
        

    def expand_source(self, source: Source) -> List[VideoTask]:
        """
        Uses yt-dlp to extract all video URLs and their duration from a given source.
        """
        video_tasks = []

        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': False,
                'force_generic_extractor': False,
                'format': 'bestaudio/best',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info_dict = ydl.extract_info(source.url, download=False)
                
                if 'entries' in info_dict:
                    for entry in info_dict['entries']:
                        if entry and entry.get('webpage_url'):
                            task = VideoTask(
                                id=str(entry.get('id', 0)),
                                source_id=str(source.id),
                                url=entry.get('webpage_url'),
                                status=self.client.config.STATUS_PENDING,
                                duration=entry.get('duration'),
                                claimed_by=None,
                                claimed_at=None,
                                retry_count=0
                            )

                            video_tasks.append(task)

                else:
                    task = VideoTask(
                        id=str(info_dict.get('id', 0)),
                        source_id=str(source.id),
                        url=info_dict.get('webpage_url'),
                        status=self.client.config.STATUS_PENDING,
                        duration=info_dict.get('duration'),
                        claimed_by=None,
                        claimed_at=None,
                        retry_count=0
                    )
                    video_tasks.append(task)
                    
            return video_tasks
        
        except yt_dlp.DownloadError as e:
            logger.error(f"Error expanding source {source.url}: {e}")
            return []
        

    def add_video_tasks_to_sheet(self, tasks: List[VideoTask]):
        """
        Adds a list of new VideoTask objects as new rows in the video tasks worksheet.
        """
        
        if not tasks:
            logger.info("No video tasks to add to the sheet.")
            return

        new_rows = []
        for task in tasks:
            row = [
                task.id,
                task.source_id,
                task.url,
                task.status,
                task.duration,
                task.claimed_by,
                task.claimed_at,
                task.retry_count
            ]

            new_rows.append(row)

        try:
            self.client.append_rows(self.client.video_tasks_worksheet, new_rows)
            logger.info(f"Successfully added {len(new_rows)} new video tasks to the sheet.")

        except Exception as e:
            logger.error(f"Failed to add video tasks to the sheet: {e}")
    
    def _find_stalled_source(self) -> Union[Dict, None]:
        """
        Scans the Sources sheet for any 'in-progress' tasks that have timed out.
        """

        records = self.client.get_sources()
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

    def mark_source_as_done(self, source_id: str):
        """
        Updates the status of a source to 'done' after successful expansion.
        """
        
        try:
            self.client.update_row(
                worksheet=self.client.sources_worksheet,
                row_id=str(source_id),
                updates={'Status': self.client.config.STATUS_DONE}
            )
            logger.info(f"Source ID {source_id} marked as done.")
        
        except Exception as e:
            logger.error(f"Failed to mark source ID {source_id} as done: {e}")

    def mark_source_as_error(self, source_id: str):
        """
        Updates the status of a source to 'error' if expansion fails.
        """
        
        try:
            self.client.update_row(
                worksheet=self.client.sources_worksheet,
                row_id=str(source_id),
                updates={'Status': self.client.config.STATUS_ERROR}
            )
            logger.info(f"Source ID {source_id} marked as error.")
        
        except Exception as e:
            logger.error(f"Failed to mark source ID {source_id} as error: {e}")
