import logging
import time
from typing import Set

from .sheet_client import SheetClient


logger = logging.getLogger(__name__)


def import_sources_from_file(file_path: str, client: SheetClient):
    """
    Reads a text file to add new sources to the Google Sheet.

    This function parses a file where each line contains '|'-separated values.
    The parameters are passed to the client strictly in the order they appear.
    The first parameter of each line is treated as the URL for duplicate checking.
    """

    try:
        logger.info("Fetching existing sources to avoid duplicates...")

        existing_sources = client.get_sources()
        existing_urls: Set[str] = {source.get('URL', '').strip() for source in existing_sources}

        logger.info("Found %d existing sources.", len(existing_urls))

        sources_added_count = 0
        sources_skipped_count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                parts = [part.strip() for part in line.split('|')]

                if not parts or not parts[0]:
                    logger.warning("Warning: Skipping line %d as it's empty or missing a URL.", i)
                    continue
                
                url = parts[0]

                if url in existing_urls:
                    logger.info("Skipping duplicate URL: %s", url)
                    sources_skipped_count += 1
                
                else:
                    logger.info("Adding new source: %s", url)
                    
                    client.add_source(*parts)
                    
                    existing_urls.add(url)
                    sources_added_count += 1

                    time.sleep(client.config.api_wait_seconds)

        summary_message = (
            f"Import Summary: {sources_added_count} sources added, {sources_skipped_count} duplicates skipped."
        )
        logger.info(summary_message)

    except FileNotFoundError:
        logger.error("Error: The file '%s' was not found.", file_path)
        
    except Exception:
        logger.exception("An unexpected error occurred while importing from '%s'", file_path)