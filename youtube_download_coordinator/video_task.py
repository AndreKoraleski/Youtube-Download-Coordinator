from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class VideoTask:
    """
    A data class to represent a single video task.

    This class provides a structured way to handle video information retrieved from
    the Google Sheets document. Tasks now have minimal columns and reference the
    source via SourceID for additional metadata.
    """

    id: str
    source_id: str
    url: str
    status: str
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    duration: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None


    @classmethod
    def from_dict(cls, data: Dict) -> 'VideoTask':
        """
        Creates a VideoTask instance from a dictionary row retrieved from gspread.
        """

        duration = data.get('Duration')

        if duration and str(duration).strip():

            try:
                duration = int(float(duration))

            except (ValueError, TypeError):
                duration = None
                
        else:
            duration = None

        return cls(
            id=data.get('ID', ''),
            source_id=data.get('SourceID', ''),
            url=data.get('URL', ''),
            status=data.get('Status', 'pending'),
            claimed_by=data.get('ClaimedBy'),
            claimed_at=data.get('ClaimedAt'),
            duration=duration,
            retry_count=int(data.get('RetryCount', 0)),
            error_message=data.get('ErrorMessage')
        )