"""Utility functions for Space Hog."""

from dataclasses import dataclass
import logging
import os
from pathlib import Path


@dataclass
class FileInfo:
    """Information about a file."""
    path: Path
    size: int

    @property
    def size_human(self) -> str:
        return format_size(self.size)


def format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_dir_size(path: Path) -> int:
    """Calculate total size of a directory."""
    total = 0

    if not path.exists():
        return 0

    if path.is_file():
        try:
            return path.stat().st_size
        except (PermissionError, OSError) as e:
            logging.warning(f"Failed to stat file {path}: {e}")
            return 0

    def _walk_error(error: OSError):
        logging.warning(f"Failed to access {getattr(error, 'filename', path)}: {error}")

    try:
        for root, dirnames, filenames in os.walk(path, topdown=True, followlinks=False, onerror=_walk_error):
            # Prune symlinked directories defensively.
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if not (Path(root) / dirname).is_symlink()
            ]

            for filename in filenames:
                entry = Path(root) / filename
                try:
                    if not entry.is_symlink():
                        total += entry.stat().st_size
                except (PermissionError, OSError) as e:
                    logging.warning(f"Failed to stat file {entry}: {e}")
    except (PermissionError, OSError) as e:
        logging.warning(f"Failed to walk directory {path}: {e}")
    return total


def print_header(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
