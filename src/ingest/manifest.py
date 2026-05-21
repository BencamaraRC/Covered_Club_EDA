"""
Download manifest. Tracks what was downloaded, when, and the URL used.
Every fetch() call writes a row here so you have an audit trail.
"""
from __future__ import annotations
import csv
import datetime as dt
from pathlib import Path
from config import DATA_DIR

MANIFEST_PATH = DATA_DIR / "manifest.csv"
HEADERS = ["timestamp", "source", "url", "local_path", "size_bytes", "status"]


def log(source: str, url: str, local_path: Path, status: str = "ok") -> None:
    """Append a row to the manifest. Creates header if file doesn't exist."""
    new_file = not MANIFEST_PATH.exists()
    size = local_path.stat().st_size if local_path.exists() else 0

    with open(MANIFEST_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(HEADERS)
        writer.writerow([
            dt.datetime.now().isoformat(timespec="seconds"),
            source,
            url,
            str(local_path),
            size,
            status,
        ])


def read() -> list[dict]:
    """Read the manifest as a list of dicts."""
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))
