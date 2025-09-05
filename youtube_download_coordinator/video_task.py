from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class VideoTask:
    """
    A data class to represent a single video task.

    This class provides a structured way to handle video information retrieved from
    the Google Sheets document, making the code cleaner and less prone to errors
    compared to using raw dictionaries.
    """

    id: int
    source_id: int
    url: str
    status: str
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    accent: Optional[str] = None
    task_type: Optional[str] = None
    duration: Optional[int] = None
    retry_count: int = 0


    @classmethod
    def from_dict(cls, data: Dict) -> 'VideoTask':
        """
        Creates a VideoTask instance from a dictionary row retrieved from gspread.
        """

        return cls(
            id=int(data.get('ID', 0)),
            source_id=int(data.get('SourceID', 0)),
            url=data.get('URL', ''),
            status=data.get('Status', 'pending'),
            claimed_by=data.get('ClaimedBy'),
            claimed_at=data.get('ClaimedAt'),
            accent=data.get('Accent'),
            task_type=data.get('Type'),
            duration=data.get('Duration'),
            retry_count=int(data.get('RetryCount', 0))
        )