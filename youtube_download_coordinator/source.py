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
    speaker_gender: Optional[str] = None
    multi_speaker_percentage: Optional[float] = None
    error_message: Optional[str] = None


    @classmethod
    def from_dict(cls, data: Dict) -> 'Source':
        """
        Creates a Source instance from a dictionary row retrieved from gspread.
        """

        multi_speaker_percentage = data.get('MultiSpeakerPercentage')

        if multi_speaker_percentage and str(multi_speaker_percentage).strip():
            
            try:
                multi_speaker_percentage = float(multi_speaker_percentage)
            
            except (ValueError, TypeError):
                multi_speaker_percentage = None
        else:
            multi_speaker_percentage = None

        return cls(
            id=data.get('ID', ''),
            url=data.get('URL', ''),
            status=data.get('Status', 'pending'),
            claimed_by=data.get('ClaimedBy'),
            claimed_at=data.get('ClaimedAt'),
            accent=data.get('Accent'),
            source_type=data.get('Type'),
            speaker_gender=data.get('SpeakerGender'),
            multi_speaker_percentage=multi_speaker_percentage,
            error_message=data.get('ErrorMessage')
        )