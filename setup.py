from pathlib import Path
from setuptools import setup, find_packages
from typing import List


def read_file(filename: str) -> str:
    """
    Read a file with robust encoding handling.
    """
    filepath = Path(filename)
    if not filepath.exists():
        return ""

    encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
    for encoding in encodings:
        try:
            return filepath.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError, OSError):
            continue

    try:
        return filepath.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""


def parse_requirements(filename: str = "requirements.txt") -> List[str]:
    """
    Parse requirements from requirements.txt file.
    """
    content = read_file(filename)
    if not content:
        return []

    requirements = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "-e")):
            requirements.append(line)

    return requirements


long_description = Path("README.md").read_text(encoding="utf-8")
requirements = parse_requirements()

PACKAGE_INFO = {
    "name": "yt-download-coordinator",
    "version": "0.1.0",
    "author": "Andre Koraleski",
    "author_email": "andrekorale@gmail.com",
    "description": (
        "A distributed task coordinator for downloading YouTube videos using Google Sheets"
    ),
    "long_description": long_description,
    "long_description_content_type": "text/markdown",
    "url": "https://github.com/AndreKoraleski/Youtube-Download-Coordinator",
    "packages": find_packages(exclude=("tests*", "docs*", "examples*")),
    "install_requires": requirements,
    "license": "GPL-3.0-only",
    "classifiers": [
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    "python_requires": ">=3.8",
}

setup(**PACKAGE_INFO)
