# YouTube Download Coordinator

A distributed task coordinator for downloading YouTube videos (or performing any other YouTube-video-related tasks) using Google Sheets as a centralized task queue. This system allows multiple machines to work together, automatically expanding YouTube channels/playlists into individual video tasks and coordinating the work across workers.

## Features

- **Distributed Task Processing**: Multiple machines can work on the same queue simultaneously
- **Google Sheets Integration**: Uses Google Sheets as a centralized, human-readable task queue
- **Automatic Source Expansion**: Converts YouTube channels, playlists, and individual videos into individual tasks
- **Fault Tolerance**: Handles stalled tasks, retries, and dead-letter queues for problematic content
- **File-based Source Import**: Automatically imports new sources from text files
- **Worker Health Monitoring**: Tracks worker status and activity
- **Result Management**: Organizes downloaded content and provides tools for result handling

## Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account with Sheets API enabled
- Google Service Account credentials with access to your target spreadsheet

## Installation



### Option 1: Install from Source
```bash
git clone https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git
cd Youtube-Download-Coordinator
pip install -e .
```

### We are considering adding a PyPI way to install.

## Setup

### 1. Google Sheets Setup

1. Create a Google Spreadsheet with the following worksheets:
   - **Sources**: Where YouTube channels/playlists are added
   - **Video Tasks**: Individual video download tasks
   - **Dead-Letter Sources**: Failed sources after max retries
   - **Dead-Letter Tasks**: Failed tasks after max retries  
   - **Workers**: Worker status and health monitoring

2. Set up the required columns in each worksheet:

**Sources Worksheet:**
```
ID | URL | Status | ClaimedBy | ClaimedAt | Name | Gender | Accent | ContentType | Type | MultispeakerPercentage | RetryCount | LastError
```

**Video Tasks Worksheet:**
```
ID | SourceID | URL | Status | Duration | ClaimedBy | ClaimedAt | RetryCount | LastError
```

**Workers Worksheet:**
```
Hostname | LastSeen | Status
```

### 2. Google Cloud Credentials

1. Create a Google Cloud Project
2. Enable the Google Sheets API
3. Create a Service Account and download the JSON credentials file
4. Share your Google Spreadsheet with the service account email (give Editor permissions)

### 3. Configuration

Create your configuration and initialize the coordinator:

```python
from youtube_download_coordinator import Config, Coordinator

config = Config(
    credentials_file="path/to/your/credentials.json",
    spreadsheet_id="your_google_sheets_id",
    sources_file_path="sources.txt",  # Optional: for file-based source import
    results_dir="downloads",
    selected_dir="selected"
)

coordinator = Coordinator(config)
```

## Usage

### Basic Usage Pattern

```python
import yt_dlp
from youtube_download_coordinator import Config, Coordinator

def download_video(url: str):
    """Your custom processing function"""
    ydl_opts = {
        'outtmpl': f'{config.results_dir}/%(id)s/%(title)s.%(ext)s',
        # Add your yt-dlp options here
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

config = Config(
    credentials_file="credentials.json",
    spreadsheet_id="your_sheets_id"
)

coordinator = Coordinator(config)

# Process tasks continuously
while True:
    if not coordinator.process_next_task(download_video):
        print("No tasks available, waiting...")
        time.sleep(30)
```

### File-based Source Import

Create a `sources.txt` file with one source per line:
```
https://www.youtube.com/@channel1|Channel Name|Female|American|Educational|Channel|15.5
https://www.youtube.com/playlist?list=PLxxx|Playlist Name|Male|British|Entertainment|Playlist|5.0
https://www.youtube.com/watch?v=xxxxx|Video Title|Female|Canadian|Tutorial|Video|0
```

Format: `URL|Name|Gender|Accent|ContentType|Type|MultispeakerPercentage`

The coordinator will automatically import new sources when the file changes.

### Result Management

```python
# Move results for a specific source to the selected directory
coordinator.manage_results(source_id="123")

# Move all results back to the main results directory
coordinator.manage_results()
```

## Configuration Options

The `Config` class supports extensive customization:

### Core Settings
- `credentials_file`: Path to Google Service Account JSON file
- `spreadsheet_id`: Google Sheets document ID
- `sources_file_path`: Optional path to sources import file
- `results_dir`: Directory for downloaded content (default: 'results')
- `selected_dir`: Directory for selected results (default: 'selected')
- `api_wait_seconds`: Delay between API calls (default: 1.0)

### Worksheet Names
- `sources_worksheet_name`: Name of sources worksheet (default: 'Sources')
- `video_tasks_worksheet_name`: Name of video tasks worksheet (default: 'Video Tasks')
- `source_dead_letter_worksheet_name`: Dead letter sources (default: 'Dead-Letter Sources')
- `task_dead_letter_worksheet_name`: Dead letter tasks (default: 'Dead-Letter Tasks')
- `workers_worksheet_name`: Worker monitoring (default: 'Workers')

### Status Values
- `STATUS_PENDING`: 'pending'
- `STATUS_IN_PROGRESS`: 'in-progress'  
- `STATUS_DONE`: 'done'
- `STATUS_ERROR`: 'error'
- `STATUS_ACTIVE`: 'active'

### Distributed System Tuning
- `claim_jitter_seconds`: Random delay when claiming tasks (default: 5)
- `stalled_task_timeout_minutes`: Timeout for stalled tasks (default: 60)
- `max_retries`: Maximum retry attempts (default: 3)
- `video_task_batch_size`: Batch size for adding tasks (default: 25)
- `health_check_interval_seconds`: Worker health check frequency (default: 60)

### Error Handling
- `fatal_error_substrings`: List of error messages that trigger immediate dead-lettering

## Architecture

### Task Flow
1. **Sources**: YouTube URLs (channels, playlists, videos) are added to the Sources worksheet
2. **Expansion**: Workers claim sources and expand them into individual video tasks
3. **Processing**: Workers claim video tasks and execute your custom processing function
4. **Results**: Completed tasks are marked as done, failed tasks are retried or dead-lettered

### Fault Tolerance
- **Stalled Task Recovery**: Automatically detects and recovers stalled tasks
- **Retry Logic**: Failed tasks are retried up to the maximum retry limit
- **Dead Letter Queues**: Permanently failed tasks/sources are moved to separate worksheets
- **Claim Verification**: Ensures only one worker can claim a task at a time

### Worker Coordination  
- **Health Monitoring**: Workers periodically report their status
- **Jittered Claims**: Random delays prevent thundering herd problems
- **Atomic Operations**: Sheet updates use atomic claim-and-verify patterns

## Monitoring

Monitor your system through the Google Sheets interface:

- **Sources worksheet**: Track source expansion progress
- **Video Tasks worksheet**: Monitor individual task status
- **Workers worksheet**: View active workers and their last activity
- **Dead Letter worksheets**: Review failed tasks that need attention

## Troubleshooting

### Common Issues

**Authentication Errors**
- Verify your service account JSON file path is correct
- Ensure the service account has access to your spreadsheet
- Check that the Sheets API is enabled in Google Cloud

**No Tasks Found**
- Verify worksheet names match your configuration
- Check that sources have 'pending' status
- Ensure your spreadsheet has the correct column headers

**Tasks Getting Stuck**
- Check the `stalled_task_timeout_minutes` setting
- Review the dead letter queues for error patterns
- Verify your processing function handles errors properly

### Debug Logging

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('youtube_download_coordinator')
logger.setLevel(logging.DEBUG)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube content extraction

