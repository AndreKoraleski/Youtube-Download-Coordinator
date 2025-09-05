# YouTube Download Coordinator
A distributed task coordinator for downloading YouTube videos using Google Sheets as backend. This package was designed to be integrated into larger systems that need distributed video processing.

## Overview
The Download Coordinator allows multiple machines to work coordinately to process YouTube playlists and channels, expanding them into individual video tasks and managing processing state through Google Sheets.

### Key Features
- **Distributed Processing**: Multiple instances can work simultaneously without conflicts
- **State Management**: Uses Google Sheets as a distributed database
- **Failure Recovery**: Automatic retry system and dead-letter queue
- **Duplicate Prevention**: Avoids processing the same source multiple times
- **Task Timeout**: Detects and reprocesses stalled tasks

## Installation

### Prerequisites
1. **Google Cloud Account** with Google Sheets API enabled
2. **Service Account** with editor permissions on the spreadsheet
3. **Python 3.6+**

### Library Installation
Install directly from the Git repository:

```bash
pip install git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git
```

Or for a specific branch/tag:
```bash
pip install git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git@main
```

For development installation (editable mode):
```bash
pip install -e git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git#egg=youtube-download-coordinator
```

### Dependencies
The package automatically installs:
- `gspread` - Google Sheets client
- `yt-dlp` - YouTube information extractor
- Other dependencies listed in `requirements.txt`

## Configuration

### 1. Google Sheets Setup

#### Create Service Account
1. Access the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create a Service Account
5. Download the JSON credentials file

#### Prepare the Spreadsheet
Create a Google Sheets spreadsheet with the following tabs:

**"Sources" Tab** with columns:
- `ID` (auto-numbered)
- `URL` (channel/playlist URL)
- `Status` (pending/in-progress/done/error)
- `ClaimedBy` (machine hostname)
- `ClaimedAt` (timestamp)
- `Accent` (accent/language)
- `Type` (type of videos in the source)

**"Video Tasks" Tab** with columns:
- `ID` (auto-numbered)
- `SourceID` (source reference)
- `URL` (individual video URL)
- `Status` (pending/in-progress/done/error)
- `ClaimedBy` (machine hostname)
- `ClaimedAt` (timestamp)
- `Accent` (accent/language)
- `Type` (same type as the source)
- `Duration` (duration in seconds)
- `RetryCount` (attempt counter)

**"Dead-Letter Queue" Tab** (same columns as Video Tasks)

### 2. Permissions
Share the spreadsheet with the Service Account email giving **Editor** permission.

## Usage

### Basic Configuration
```python
from youtube_download_coordinator import Config, Coordinator

# Configure the system
config = Config(
    credentials_file="path/to/service-account.json",
    spreadsheet_id="your-spreadsheet-id-here",
    sources_file_path="sources.txt"  # Optional
)

# Initialize the coordinator
coordinator = Coordinator(config)
```

### Main Processing Function
The main method that should be called in your larger system is `process_next_task()`:

```python
def my_download_function(url: str):
    """
    Your custom function that processes the video
    Args:
        url: Video URL to process
    """
    print(f"Processing video: {url}")
    # Your download logic here
    # For example: download audio, transcribe, etc.

# Main loop of your system
while True:
    # Process the next available task
    task_processed = coordinator.process_next_task(my_download_function)
    
    if not task_processed:
        print("No tasks available. Waiting...")
        time.sleep(30)  # Wait before trying again
```

### Complete Example
```python
import time
import logging
from download_coordinator import Config, Coordinator

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configuration
config = Config(
    credentials_file="credentials.json",
    spreadsheet_id="1ABC123-your-spreadsheet-id",
    sources_file_path="new_sources.txt"
)

# Initialize coordinator
coordinator = Coordinator(config)

def process_video(url: str):
    """Example processing function"""
    try:
        print(f"Starting download: {url}")
        # Your logic here (download, processing, etc.)
        time.sleep(5)  # Simulate processing
        print(f"Completed: {url}")
        
    except Exception as e:
        print(f"Error processing {url}: {e}")
        raise  # Re-raise so coordinator marks as error

# Main loop
def main():
    print("Starting download coordinator...")
    
    while True:
        try:
            # Try to process a task
            if coordinator.process_next_task(process_video):
                print("Task processed successfully")
            else:
                print("No tasks available")
                time.sleep(60)  # Wait 1 minute
                
        except KeyboardInterrupt:
            print("Stopping coordinator...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(30)  # Wait before trying again

if __name__ == "__main__":
    main()
```

## Adding New Sources

### Via Text File
Create a `sources.txt` file with the format:
```
https://youtube.com/playlist?list=PLrAXtmRdnEQy5VFhr|pt-BR|playlist
https://youtube.com/@examplechannel|en-US|channel
```
Format: `URL|Accent|Type`

### Programmatically
```python
# Add individual source
coordinator.client.add_source(
    url="https://youtube.com/playlist?list=PLexample",
    accent="pt-BR",
    source_type="playlist"
)
```

## Advanced Configuration

### Adjust Timeouts and Retry
```python
config = Config(
    credentials_file="credentials.json",
    spreadsheet_id="your-id",
    # Distributed system settings
    claim_jitter_seconds=10,           # Jitter to avoid race conditions
    stalled_task_timeout_minutes=120,  # Timeout for stalled tasks
    max_retries=5                      # Max attempts before dead-letter
)
```

### Customize Spreadsheet Names
```python
config = Config(
    credentials_file="credentials.json",
    spreadsheet_id="your-id",
    # Custom tab names
    sources_worksheet_name='MySources',
    video_tasks_worksheet_name='MyTasks',
    dead_letter_worksheet_name='FailedTasks'
)
```

## Integration in Larger Systems

### As a Microservice
```python
# worker.py
import os
from download_coordinator import Config, Coordinator
from my_system import process_complete_video

config = Config(
    credentials_file=os.getenv("GOOGLE_CREDENTIALS"),
    spreadsheet_id=os.getenv("SPREADSHEET_ID")
)

coordinator = Coordinator(config)

# Worker infinite loop
while True:
    coordinator.process_next_task(process_complete_video)
```

### With Celery/RQ
```python
from celery import Celery
from download_coordinator import Config, Coordinator

app = Celery('video_processor')

@app.task
def process_next_task():
    coordinator = Coordinator(config)
    return coordinator.process_next_task(my_processing_function)

# Schedule periodic execution
from celery.schedules import crontab

app.conf.beat_schedule = {
    'process-tasks': {
        'task': 'process_next_task',
        'schedule': 60.0,  # Every 60 seconds
    },
}
```

### Installing in Requirements Files
For `requirements.txt`:
```
git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git
```

For `setup.py` or `pyproject.toml`:
```python
# setup.py
install_requires=[
    "youtube-download-coordinator @ git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git"
]

# pyproject.toml
dependencies = [
    "youtube-download-coordinator @ git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git"
]
```

## Monitoring

### Logs
The system generates detailed logs. Configure the appropriate level:
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Task Status
Monitor directly in the Google Sheets or programmatically:
```python
# Check statistics
sources = coordinator.client.get_sources()
tasks = coordinator.client.get_video_tasks()

pending_sources = len([s for s in sources if s['Status'] == 'pending'])
pending_tasks = len([t for t in tasks if t['Status'] == 'pending'])

print(f"Pending sources: {pending_sources}")
print(f"Pending tasks: {pending_tasks}")
```

## Troubleshooting

### Common Errors
1. **FileNotFoundError**: Check the credentials file path
2. **SpreadsheetNotFound**: Check spreadsheet ID and permissions
3. **APIError**: Check if Service Account has editor permissions

### Stalled Task Recovery
The system automatically detects stalled tasks based on the configured timeout and puts them back in the queue.

### Dead Letter Queue
Tasks that failed multiple times are moved to the "Dead-Letter Queue" tab for manual analysis.

## Updating the Library

To update to the latest version:
```bash
pip install --upgrade git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git
```

To install a specific commit or tag:
```bash
pip install git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git@v1.0.0
pip install git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git@commit-hash
```

## Contributing

This package was developed for specific use cases. For modifications:
1. Fork the repository
2. Clone your fork locally
3. Install in development mode: `pip install -e .`
4. Make your modifications
5. Test in distributed environment
6. Submit a pull request

## License

GNU General Public License v3.0 (GPL v3)

This project is open source and can be used for commercial purposes, provided that:
- Modifications are shared under the same GPL v3 license
- Source code of modifications is made available
- End-user rights are preserved

See the LICENSE file for complete details.