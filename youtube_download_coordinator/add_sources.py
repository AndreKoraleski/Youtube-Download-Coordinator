import logging
import time
from typing import Set

from .sheet_client import SheetClient


logger = logging.getLogger(__name__)


def import_sources_from_file(file_path: str, client: SheetClient):
    """
    Reads a text file to add new sources to the Google Sheet.

    This function parses a file where each line should be in the format
    URL|Accent|Type, checks for duplicates, and adds only new sources
    to the 'Sources' sheet.
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

                parts = line.split('|')
                if len(parts) != 3:
                    logger.warning("Warning: Skipping malformed line %d: %s", i, line)
                    continue

                url, accent, source_type = [part.strip() for part in parts]

                if url in existing_urls:
                    logger.info("Skipping duplicate URL: %s", url)
                    sources_skipped_count += 1
                else:
                    logger.info("Adding new source: %s", url)
                    client.add_source(url, accent, source_type)
                    existing_urls.add(url)
                    sources_added_count += 1
                    time.sleep(1.5)

        summary_message = (
            "\n--- Import Summary ---\n"
            f"Sources successfully added: {sources_added_count}\n"
            f"Sources skipped (duplicates): {sources_skipped_count}\n"
            "---------------------------"
        )
        logger.info(summary_message)

    except FileNotFoundError:
        logger.error("Error: The file '%s' was not found.", file_path)
    except Exception:
        logger.exception("An unexpected error occurred while importing from '%s'", file_path)
