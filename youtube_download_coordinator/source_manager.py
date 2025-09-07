import logging
import random
import time
from typing import Dict, List, Union, Iterator, Set

import yt_dlp

from .sheet_client import SheetClient
from .source import Source
from .video_task import VideoTask
from .utils.time_utils import get_current_timestamp
from .utils.system_utils import get_machine_hostname


logger = logging.getLogger(__name__)


class SourceManager:
    """
    Manages expanding a YouTube source into individual video tasks on the spreadsheet.
    It validates video data, prevents duplicates, and adds tasks in batches.
    """

    def __init__(self, sheet_client: SheetClient):
        """
        Initializes the SourceManager with a SheetClient instance.
        """

        self.client = sheet_client


    def get_next_source_to_expand(self) -> Union[Source, None]:
        """
        Claims the next pending source from the spreadsheet for expansion.
        """

        time.sleep(random.uniform(0, self.client.config.claim_jitter_seconds))

        stalled_source_data = self._find_stalled_source()
        if stalled_source_data:
            self._reset_stalled_source(stalled_source_data)

        source_data = self.client.find_next_pending_source()
        if not source_data:
            return None
        
        source_id = str(source_data.get('ID'))
        hostname = get_machine_hostname()
        timestamp = get_current_timestamp()

        try:
            self.client.update_row(
                worksheet=self.client.sources_worksheet,
                row_id=source_id,
                updates={
                    'Status': self.client.config.STATUS_IN_PROGRESS,
                    'ClaimedBy': hostname,
                    'ClaimedAt': timestamp
                }
            )
            re_read_source = self.client._get_source_by_id(source_id)

            if re_read_source and re_read_source.get('ClaimedBy') == hostname:
                logger.info(f"Successfully claimed source ID {source_id}.")
                return Source.from_dict(re_read_source)
            else:
                logger.warning(f"Failed to claim source ID {source_id}. Another machine claimed it first.")
                return None
        
        except Exception as e:
            logger.error(f"Failed to claim source ID {source_id}: {e}")
            return None
        

    def _extract_videos_from_source(self, source: Source) -> Iterator[VideoTask]:
        """
        Uses yt-dlp to extract all video data from a source URL and yields
        validated VideoTask objects. This is a generator for memory efficiency.
        """

        ydl_opts = {'quiet': True, 'extract_flat': False, 'force_generic_extractor': False}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(source.url, download=False)
                
                entries = info_dict.get('entries', [info_dict] if info_dict else [])
                
                for entry in entries:
                    if not (entry and entry.get('id') and entry.get('webpage_url')):
                        logger.warning(f"Skipping invalid video entry from source {source.id}")
                        continue

                    yield VideoTask(
                        id=str(entry['id']),
                        source_id=str(source.id),
                        url=entry['webpage_url'],
                        status=self.client.config.STATUS_PENDING,
                        duration=entry.get('duration'),
                    )
        except yt_dlp.DownloadError as e:
            logger.error(f"yt-dlp error expanding source {source.url}: {e}")
            raise  


    def process_source_expansion(self, source: Source) -> bool:
        """
        Orchestrates the entire source expansion process.
        """

        try:
            logger.info("Fetching existing video tasks to prevent duplicates...")
            existing_tasks = self.client.get_video_tasks()
            existing_video_ids: Set[str] = {str(task.get('ID')) for task in existing_tasks}
            logger.info(f"Found {len(existing_video_ids)} existing video tasks.")

            logger.info(f"Starting video extraction from source {source.id}. This may take a moment...")
            
            all_tasks_from_source = list(self._extract_videos_from_source(source))
            
            logger.info(f"Extraction complete. Found {len(all_tasks_from_source)} total videos. Now filtering and batching.")

            batch = []
            total_added = 0
            total_skipped = 0
            batch_size = self.client.config.video_task_batch_size

            for task in all_tasks_from_source:
                if task.id not in existing_video_ids:
                    batch.append(task)
                    existing_video_ids.add(task.id)
                    
                    if len(batch) >= batch_size:
                        self._add_video_tasks_batch_to_sheet(batch)
                        total_added += len(batch)
                        batch = []
                else:
                    total_skipped += 1
            
            if batch:
                self._add_video_tasks_batch_to_sheet(batch)
                total_added += len(batch)
            
            logger.info(
                f"Source expansion summary for source ID {source.id}: "
                f"{total_added} new tasks added, {total_skipped} duplicates skipped."
            )
            self.mark_source_as_done(str(source.id))
            return True

        except Exception:
            logger.exception(f"Failed to expand source ID {source.id}.")
            self.mark_source_as_error(source)
            return False


    def _add_video_tasks_batch_to_sheet(self, tasks_batch: List[VideoTask]):
        """
        Converts a batch of VideoTask objects to a list of lists and appends them to the sheet.
        """
        if not tasks_batch:
            return
        
        new_rows = [
            [
                task.id, task.source_id, task.url, task.status, task.duration,
                task.claimed_by, task.claimed_at, task.retry_count
            ] for task in tasks_batch
        ]

        try:
            self.client.append_rows(self.client.video_tasks_worksheet, new_rows)
            logger.info(f"Successfully added a batch of {len(new_rows)} new video tasks.")
        except Exception:
            logger.error("Failed to add a batch of video tasks to the sheet.")
            raise


    def _find_stalled_source(self) -> Union[Dict, None]:
        """
        Scans the Sources sheet for any 'in-progress' sources that have timed out.
        """
        records = self.client.get_sources()
        current_time_epoch = time.time()
        timeout_seconds = self.client.config.stalled_task_timeout_minutes * 60

        for record in records:
            if record.get('Status') == self.client.config.STATUS_IN_PROGRESS:
                claimed_at_str = record.get('ClaimedAt')
                if claimed_at_str:
                    try:
                        claimed_at_epoch = time.mktime(time.strptime(claimed_at_str, "%Y-%m-%d %H:%M:%S"))
                        if (current_time_epoch - claimed_at_epoch) > timeout_seconds:
                            logger.warning(f"Found stalled source: ID {record.get('ID')}")
                            return record
                    except ValueError:
                        logger.error(f"Could not parse ClaimedAt timestamp for source ID {record.get('ID')}")
        return None


    def _reset_stalled_source(self, source_data: Dict):
        """Resets a stalled source to 'pending' and increments its retry count."""
        try:
            new_retry_count = int(source_data.get('RetryCount', 0)) + 1
            self.client.update_row(
                worksheet=self.client.sources_worksheet,
                row_id=str(source_data.get('ID')),
                updates={
                    'Status': self.client.config.STATUS_PENDING,
                    'ClaimedBy': '',
                    'ClaimedAt': '',
                    'RetryCount': new_retry_count
                }
            )
            logger.info(f"Reset stalled source with ID {source_data.get('ID')} to 'pending'.")
            time.sleep(self.client.config.api_wait_seconds)
        except Exception as e:
            logger.error(f"Failed to reset stalled source ID {source_data.get('ID')}: {e}")


    def mark_source_as_done(self, source_id: str):
        """Updates the status of a source to 'done' after successful expansion."""
        try:
            self.client.update_row(
                worksheet=self.client.sources_worksheet,
                row_id=source_id,
                updates={'Status': self.client.config.STATUS_DONE}
            )
            logger.info(f"Source ID {source_id} marked as done.")
        except Exception as e:
            logger.error(f"Failed to mark source ID {source_id} as done: {e}")


    def mark_source_as_error(self, source_id: str):
        """Updates the status of a source to 'error' if expansion fails."""
        try:
            self.client.update_row(
                worksheet=self.client.sources_worksheet,
                row_id=source_id,
                updates={'Status': self.client.config.STATUS_ERROR}
            )
            logger.info(f"Source ID {source_id} marked as error.")
        except Exception as e:
            logger.error(f"Failed to mark source ID {source_id} as error: {e}")