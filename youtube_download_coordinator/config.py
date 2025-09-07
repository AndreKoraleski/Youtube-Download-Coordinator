from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


@dataclass
class Config:
    """
    Configuration settings for the Download Coordinator.
    """
    # --- Core Settings ---
    credentials_file: str
    spreadsheet_id: str
    sources_file_path: Optional[str] = None
    api_wait_seconds: float = 3.0

    # --- Worksheet Names ---
    sources_worksheet_name: str = 'Sources'
    video_tasks_worksheet_name: str = 'Video Tasks'
    source_dead_letter_worksheet_name: str = 'Dead-Letter Sources'
    task_dead_letter_worksheet_name: str = 'Dead-Letter Tasks'

    # --- Status Constants ---
    STATUS_PENDING: str = 'pending'
    STATUS_IN_PROGRESS: str = 'in-progress'
    STATUS_DONE: str = 'done'
    STATUS_ERROR: str = 'error'

    # --- Distributed System Tuning ---
    claim_jitter_seconds: int = 5
    stalled_task_timeout_minutes: int = 60
    max_retries: int = 3
    video_task_batch_size: int = 25
    
    # --- Error Handling ---
    fatal_error_substrings: List[str] = field(default_factory=lambda: [
        "Sign in to confirm your age",        # Age-restricted
        "Private video",                      # Private video
        "Video unavailable",                  # Generic unavailable
        "This video is not available",        # Region-locked/unavailable
        "This live event has ended",          # Dead livestream
        "This live stream recording is not available",
        "The uploader has not made this video available in your country",  # Geo-block
        "This video has been removed for violating YouTube's Terms of Service",  # Copyright / DMCA takedown
        "This video is no longer available"   # Removed by uploader
])



    # --- Hashing Settings ---
    hash_file: str = field(init=False)

    def __post_init__(self):
        base_dir = Path(__file__).resolve().parent
        hashes_dir = base_dir / "hashes"
        hashes_dir.mkdir(parents=True, exist_ok=True)
        self.hash_file = str(hashes_dir / "sources_hash.txt")