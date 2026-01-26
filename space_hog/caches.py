"""Cache analysis for Space Hog."""

import time
from pathlib import Path

from .utils import FileInfo, get_dir_size
from .constants import CACHE_LOCATIONS


def check_caches() -> list[tuple[Path, int, str]]:
    """Check common cache locations."""
    results = []

    for location, description in CACHE_LOCATIONS:
        path = Path(location).expanduser()
        if path.exists():
            try:
                size = get_dir_size(path)
                if size > 0:
                    results.append((path, size, description))
            except (PermissionError, OSError):
                pass

    return sorted(results, key=lambda x: x[1], reverse=True)


def get_trash_size() -> int:
    """Get size of Trash folder."""
    trash_path = Path.home() / '.Trash'
    if trash_path.exists():
        return get_dir_size(trash_path)
    return 0


def get_downloads_analysis(min_age_days: int = 30) -> tuple[int, list[FileInfo]]:
    """Analyze Downloads folder for old files."""
    downloads = Path.home() / 'Downloads'
    if not downloads.exists():
        return 0, []

    cutoff = time.time() - (min_age_days * 24 * 60 * 60)
    old_files = []
    total_size = 0

    try:
        for entry in downloads.iterdir():
            if entry.is_file() and not entry.is_symlink():
                try:
                    stat = entry.stat()
                    if stat.st_mtime < cutoff:
                        old_files.append(FileInfo(entry, stat.st_size))
                        total_size += stat.st_size
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass

    return total_size, sorted(old_files, key=lambda x: x.size, reverse=True)
