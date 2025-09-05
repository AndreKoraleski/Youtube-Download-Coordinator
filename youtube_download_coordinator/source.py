from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class Source:
    """
    A data class to represent a single source for video tasks.

    This provides a structured way to handle source information from the
    Google Sheets document, including URLs and processing status.
    """
    
    id: str
    url: str
    status: str
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    accent: Optional[str] = None
    source_type: Optional[str] = None


    @classmethod
    def from_dict(cls, data: Dict) -> 'Source':
        """
        Creates a Source instance from a dictionary row retrieved from gspread.
        """

        return cls(
            id=data.get('ID', ''),
            url=data.get('URL', ''),
            status=data.get('Status', 'pending'),
            claimed_by=data.get('ClaimedBy'),
            claimed_at=data.get('ClaimedAt'),
            accent=data.get('Accent'),
            source_type=data.get('Type')
        )