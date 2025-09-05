import gspread
from gspread import Worksheet
from gspread.exceptions import APIError, SpreadsheetNotFound

import logging
import time  # <--- ADICIONADO
from typing import List, Dict, Union

from .config import Config


logger = logging.getLogger(__name__)


class SheetClient:
    """
    A client for all Google Sheets API interactions.
    
    This class handles authentication and provides a high-level interface
    for reading from and writing to the Sources and Video Tasks worksheets.
    """

    def __init__(self, config: Config):
        """
        Initializes the SheetClient, authenticates with Google Sheets, and
        opens the required worksheets.
        """

        self.config = config
        
        self.api_wait_seconds: float = config.api_wait_seconds
        self.last_api_call_time: float = 0

        try:
            gc = gspread.service_account(filename=config.credentials_file)
            spreadsheet = gc.open_by_key(config.spreadsheet_id)

            self.sources_worksheet: Worksheet = spreadsheet.worksheet(config.sources_worksheet_name)
            self.video_tasks_worksheet: Worksheet = spreadsheet.worksheet(config.video_tasks_worksheet_name)
            self.dead_letter_worksheet: Worksheet = spreadsheet.worksheet(config.dead_letter_worksheet_name)
            
            self.last_api_call_time = time.monotonic()

            logger.info("Successfully connected to Google Sheets.")

        except FileNotFoundError:
            raise FileNotFoundError(
                f"Credentials file not found at '{config.credentials_file}'."
            )
        
        except SpreadsheetNotFound:
            raise SpreadsheetNotFound(
                f"Spreadsheet with ID '{config.spreadsheet_id}' not found or is inaccessible."
            )
        
        except APIError as e:
            raise APIError(
                f"API error occurred. Check if the service account has editor permissions. Details: {e}"
            )


    def _wait_for_api(self):
        """
        Ensures a minimum wait time between consecutive API calls to avoid rate limiting.
        """
        elapsed = time.monotonic() - self.last_api_call_time
        if elapsed < self.api_wait_seconds:
            sleep_duration = self.api_wait_seconds - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_duration:.2f} seconds.")
            time.sleep(sleep_duration)
        self.last_api_call_time = time.monotonic()


    def get_sources(self) -> List[Dict]:
        """
        Retrieves all records from the Sources worksheet.
        """
        self._wait_for_api() 
        return self.sources_worksheet.get_all_records()
    

    def get_video_tasks(self) -> List[Dict]:
        """
        Retrieves all records from the Video Tasks worksheet.
        """
        self._wait_for_api()
        return self.video_tasks_worksheet.get_all_records()
    

    def find_next_pending_source(self) -> Union[Dict, None]:
        """
        Finds the first row in the sources worksheet with a 'pending' status.
        """
        self._wait_for_api()
        try:
            status_col_index = self.sources_worksheet.row_values(1).index('Status') + 1

            self._wait_for_api()
            pending_cells = self.sources_worksheet.findall(self.config.STATUS_PENDING, in_column=status_col_index)

            if not pending_cells:
                return None

            first_pending_cell = pending_cells[0]

            self._wait_for_api()
            row_values = self.sources_worksheet.row_values(first_pending_cell.row)
            headers = self.sources_worksheet.row_values(1)
            
            return dict(zip(headers, row_values))

        except Exception as e:
            logger.error(f"Error finding next pending source: {e}")
            return None
        

    def find_next_pending_task(self) -> Union[Dict, None]:
        """
        Finds the first row in the video tasks worksheet with a 'pending' status.
        """
        self._wait_for_api()
        try:
            status_col_index = self.video_tasks_worksheet.row_values(1).index('Status') + 1

            self._wait_for_api()
            pending_cells = self.video_tasks_worksheet.findall(self.config.STATUS_PENDING, in_column=status_col_index)

            if not pending_cells:
                return None

            first_pending_cell = pending_cells[0]
            
            self._wait_for_api()
            row_values = self.video_tasks_worksheet.row_values(first_pending_cell.row)
            headers = self.video_tasks_worksheet.row_values(1)
            
            return dict(zip(headers, row_values))

        except Exception as e:
            logger.error(f"Error finding next pending task: {e}")
            return None
        

    def update_row(self, worksheet: Worksheet, row_id: int, updates: Dict[str, str]):
        """
        Updates a row in a given worksheet based on its 'ID' and a dictionary of updates.
        """
        self._wait_for_api()
        all_records = worksheet.get_all_records()
        row_index = -1 

        for index, record in enumerate(all_records):
            if record.get('ID') == row_id:
                row_index = index + 2 
                break

        if row_index == -1:
            logger.warning(f"Row with ID {row_id} not found.")
            return
        
        update_list = []
        
        self._wait_for_api()
        headers = worksheet.row_values(1)
        header_map = {header: i + 1 for i, header in enumerate(headers)}

        for key, value in updates.items():
            column_index = header_map.get(key)
            if column_index:
                cell_to_update = gspread.Cell(row_index, column_index, value)
                update_list.append(cell_to_update)

        if update_list:
            self._wait_for_api()
            worksheet.update_cells(update_list)


    def append_rows(self, worksheet: Worksheet, data: List[List]):
        """
        Appends a list of rows to a specified worksheet.
        """
        if not data:
            logger.warning("No data to append.")
            return
        
        try:
            self._wait_for_api()
            worksheet.append_rows(data, value_input_option='USER_ENTERED')
            logger.info(f"Successfully appended {len(data)} rows to the '{worksheet.title}' worksheet.")
        except APIError as e:
            logger.error(f"API Error appending rows: {e}")
            raise


    def add_source(self, url: str, accent: str, source_type: str):
        """
        Adds a new source to the Sources worksheet. The ID is assumed to be
        auto-generated by the spreadsheet.
        """
        try:
            new_row = [
                '',  # ID 
                url,
                self.config.STATUS_PENDING,
                '',  # ClaimedBy
                '',  # ClaimedAt
                accent,
                source_type
            ]

            self._wait_for_api()
            self.sources_worksheet.append_row(new_row, value_input_option='USER_ENTERED')
            logger.info(f"Successfully added new source with URL: {url}")

        except Exception as e:
            logger.error(f"Failed to add new source: {e}")
            raise


    def _get_task_by_id(self, task_id: int) -> Union[Dict, None]:
        """
        Retrieves a single task record by its unique ID.
        """
        all_tasks = self.get_video_tasks()
        for task in all_tasks:
            if task.get('ID') == task_id:
                return task
        return None


    def _get_source_by_id(self, source_id: int) -> Union[Dict, None]:
        """
        Retrieves a single source record by its unique ID.
        """
        all_sources = self.get_sources()
        for source in all_sources:
            if source.get('ID') == source_id:
                return source
        return None


    def move_row_to_dead_letter(self, row_id: int):
        """
        Moves a row from the video tasks worksheet to the dead-letter worksheet.
        """
        self._wait_for_api()
        all_records = self.video_tasks_worksheet.get_all_records()
        row_index = -1
        row_to_move = None

        for index, record in enumerate(all_records):
            if record.get('ID') == row_id:
                row_index = index + 2
                self._wait_for_api()
                row_to_move = self.video_tasks_worksheet.row_values(row_index)
                break

        if not row_to_move:
            logger.warning(f"Row with ID {row_id} not found.")
            return

        try:
            self._wait_for_api()
            self.dead_letter_worksheet.append_row(row_to_move, value_input_option='USER_ENTERED')

            self._wait_for_api()
            self.video_tasks_worksheet.delete_rows(row_index)
            logger.info(f"Successfully moved row with ID {row_id} to the dead-letter queue.")
        except APIError as e:
            logger.error(f"API Error moving row to dead-letter queue: {e}")
            raise