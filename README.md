# YouTube Download Coordinator
A distributed task coordinator for downloading YouTube videos using Google Sheets as backend. This package was designed to be integrated into larger systems that need distributed video processing.

## Overview
The Download Coordinator allows multiple machines to work coordinately to process YouTube playlists and channels, expanding them into individual video tasks and managing processing state through Google Sheets.

### Key Features
- **Distributed Processing**: Multiple instances can work simultaneously without conflicts
- **State Management**: Uses Google Sheets as a distributed database
- **Failure Recovery**: Automatic retry system and separate dead-letter queues for sources and tasks
- **Error Tracking**: Detailed error messages stored in spreadsheet columns
- **Duplicate Prevention**: Avoids processing the same source multiple times
- **Task Timeout**: Detects and reprocesses stalled tasks
- **Audio Metadata**: Track speaker gender and multi-speaker audio percentage

## Installation

### Prerequisites
1. **Google Cloud Account** with Google Sheets API enabled
2. **Service Account** with editor permissions on the spreadsheet
3. **Python 3.8+**

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
- `Accent` (accent/language, e.g., "pt-BR", "en-US")
- `Type` (type of content, e.g., "playlist", "channel")
- `SpeakerGender` (e.g., "male", "female", "mixed", "unknown")
- `MultiSpeakerPercentage` (0-100, percentage of multi-speaker content)
- `ErrorMessage` (detailed error information)

**"Video Tasks" Tab** with columns:
- `ID` (auto-numbered)
- `SourceID` (reference to source ID)
- `URL` (individual video URL)
- `Status` (pending/in-progress/done/error)
- `ClaimedBy` (machine hostname)
- `ClaimedAt` (timestamp)
- `Duration` (duration in seconds)
- `RetryCount` (attempt counter)
- `ErrorMessage` (detailed error information)

**"Dead-Letter Sources" Tab** (same columns as Sources)
**"Dead-Letter Tasks" Tab** (same columns as Video Tasks)

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
    
    # If an error occurs, raise an exception with descriptive message
    # The coordinator will automatically capture and store the error
    if some_error_condition:
        raise Exception("Specific error description for troubleshooting")

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
        raise  # Re-raise so coordinator captures the specific error

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
Create a `sources.txt` file with the enhanced format:
```
https://youtube.com/playlist?list=PLrAXtmRdnEQy5VFhr|Southern|Entertainment|female|25.5
https://youtube.com/@examplechannel|Northeastern|Education|male|10.0
https://youtube.com/watch?v=example|British|Movie|mixed|75.2
```

Format: `URL|Accent|Type|SpeakerGender|MultiSpeakerPercentage`

**Simplifier:** This simplified format also works:
```
https://youtube.com/playlist?list=PLrAXtmRdnEQy5VFhr|pt-BR|playlist
https://youtube.com/@examplechannel|en-US|channel
```

### Programmatically
```python
# Add individual source with all metadata
coordinator.client.add_source(
    url="https://youtube.com/playlist?list=PLexample",
    accent="Goiano",
    source_type="educational", # Or any other tag that counts as 'type'
    speaker_gender="female",
    multi_speaker_percentage=30.5
)

# Add source with minimal data (backwards compatible)
coordinator.client.add_source(
    url="https://youtube.com/playlist?list=PLexample",
    accent="Paulista", 
    source_type="podcast"
)
```

### Error Tracking
- **Detailed Error Messages**: Both sources and tasks  store specific error messages in their `ErrorMessage` column
- **Separate Dead Letter Queues**: Sources and tasks have their own dead letter queues for failed items
- **Better Debugging**: Error messages help identify specific issues (network problems, invalid URLs, etc.)

### Audio Metadata
- **Speaker Gender**: Track the predominant speaker gender (`male`, `female`, `mixed`, `unknown`)
- **Multi-Speaker Percentage**: Percentage (0-100) indicating how much content has multiple speakers overlapping
- **Searchable Data**: Use these fields to filter content for specific use cases

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
    dead_letter_sources_worksheet_name='FailedSources',
    dead_letter_tasks_worksheet_name='FailedTasks'
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

## Monitoring and Troubleshooting

### Error Analysis
Check the `ErrorMessage` columns in both Sources and Video Tasks tables to identify patterns:
- Network connectivity issues
- Invalid URLs or private content
- yt-dlp extraction problems
- Processing function errors

### Dead Letter Queue Management
Periodically review items in the dead letter queues:
- Fix underlying issues (network, credentials, etc.)
- Move items back to pending status in main tables
- Remove permanently failed items

### Task Status Monitoring
```python
# Check statistics
sources = coordinator.client.get_sources()
tasks = coordinator.client.get_video_tasks()

pending_sources = len([s for s in sources if s['Status'] == 'pending'])
pending_tasks = len([t for t in tasks if t['Status'] == 'pending'])
error_sources = len([s for s in sources if s['Status'] == 'error'])
error_tasks = len([t for t in tasks if t['Status'] == 'error'])

print(f"Pending sources: {pending_sources}")
print(f"Pending tasks: {pending_tasks}")
print(f"Error sources: {error_sources}")
print(f"Error tasks: {error_tasks}")
```

### Logs
The system generates detailed logs. Configure the appropriate level:
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Troubleshooting

### Common Errors
1. **FileNotFoundError**: Check the credentials file path
2. **SpreadsheetNotFound**: Check spreadsheet ID and permissions
3. **APIError**: Check if Service Account has editor permissions
4. **Column Mismatch**: Ensure spreadsheet has all required columns

### Stalled Task Recovery
The system automatically detects stalled tasks based on the configured timeout and puts them back in the queue.

### Dead Letter Queue Processing
Tasks and sources that failed multiple times are moved to their respective "Dead-Letter" tabs for manual analysis.

## Updating the Library

To update to the latest version:
```bash
pip install --upgrade git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git
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