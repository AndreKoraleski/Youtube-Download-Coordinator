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
    
    name: Optional[str] = None
    gender: Optional[str] = None
    accent: Optional[str] = None
    content_type: Optional[str] = None
    source_type: Optional[str] = None
    multispeaker_percentage: Optional[float] = None

    retry_count: int = 0
    last_error: Optional[str] = None


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
            name=data.get('Name'),
            gender=data.get('Gender'),
            accent=data.get('Accent'),
            content_type=data.get('ContentType'),
            source_type=data.get('Type'),
            multispeaker_percentage=float(data['MultispeakerPercentage']) if 'MultispeakerPercentage' in data and data['MultispeakerPercentage'] not in (None, '') else None,
            retry_count=int(data.get('RetryCount', 0)) if 'RetryCount' in data and data['RetryCount'] not in (None, '') else 0,
            last_error=data.get('LastError')
        )