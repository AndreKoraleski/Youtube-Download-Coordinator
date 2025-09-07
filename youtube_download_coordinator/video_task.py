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

    id: str
    source_id: str
    url: str
    status: str
    duration: Optional[int] = None
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'VideoTask':
        """
        Creates a VideoTask instance from a dictionary row retrieved from gspread.
        """

        return cls(
            id=data.get('ID', ''),
            source_id=data.get('SourceID', ''),
            url=data.get('URL', ''),
            status=data.get('Status', 'pending'),
            duration=int(data.get('Duration')) if data.get('Duration') is not None else None,
            claimed_by=data.get('ClaimedBy'),
            claimed_at=data.get('ClaimedAt'),
            retry_count=int(data.get('RetryCount', 0)),
            last_error=data.get('LastError')
        )