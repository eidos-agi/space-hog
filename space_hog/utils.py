"""Utility functions for Space Hog."""

from dataclasses import dataclass
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
    try:
        for entry in path.rglob('*'):
            if entry.is_file() and not entry.is_symlink():
                try:
                    total += entry.stat().st_size
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass
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
