import hashlib
import logging
import time
from pathlib import Path
from typing import Set

from .sheet_client import SheetClient

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def import_sources_from_file(file_path: str, client: SheetClient):
    """
    Reads a text file to add new sources to the Google Sheet.
    Only runs if the file has changed since the last run (tracked in client.config.hash_file).
    Safely ensures the file exists before processing.
    """
    file_path_obj = Path(file_path)
    file_path_obj.parent.mkdir(parents=True, exist_ok=True)  

    if not file_path_obj.exists():
        logger.warning("File '%s' does not exist. Creating an empty file.", file_path)
        file_path_obj.touch()

    try:
        file_hash = calculate_file_hash(file_path)
        hash_file = client.config.hash_file

        hash_file_obj = Path(hash_file)
        hash_file_obj.parent.mkdir(parents=True, exist_ok=True)
        
        if not hash_file_obj.exists():
            hash_file_obj.touch()

        try:
            with open(hash_file, "r", encoding="utf-8") as f:
                last_hash = f.read().strip()
        except FileNotFoundError:
            last_hash = ""

        if last_hash == file_hash:
            logger.info("No changes detected in '%s'. Skipping import.", file_path)
            return
        else:
            logger.info("Change detected in '%s'. Proceeding with import.", file_path)

        logger.info("Fetching existing sources to avoid duplicates...")
        existing_sources = client.get_sources()
        existing_urls: Set[str] = {source.get("URL", "").strip() for source in existing_sources}
        logger.info("Found %d existing sources.", len(existing_urls))

        sources_added_count = 0
        sources_skipped_count = 0

        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                parts = [part.strip() for part in line.split("|")]
                if not parts or not parts[0]:
                    logger.warning("Skipping line %d as it's empty or missing a URL.", i)
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

        with open(hash_file, "w", encoding="utf-8") as f:
            f.write(file_hash)

    except Exception:
        logger.exception("An unexpected error occurred while importing from '%s'", file_path)
