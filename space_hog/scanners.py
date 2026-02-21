"""File system scanners for Space Hog."""

import hashlib
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Generator

from .utils import FileInfo, get_dir_size
from .constants import SPACE_HOG_PATTERNS


def find_large_files(root: Path, min_size_mb: int = 100) -> Generator[FileInfo, None, None]:
    """Find files larger than min_size_mb."""
    min_size = min_size_mb * 1024 * 1024

    def _walk_error(error: OSError):
        logging.warning(f"Failed to scan path {getattr(error, 'filename', root)}: {error}")

    try:
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False, onerror=_walk_error):
            dirnames[:] = [
                d for d in dirnames
                if not os.path.islink(os.path.join(dirpath, d))
            ]
            for filename in filenames:
                entry = Path(dirpath) / filename
                if entry.is_symlink():
                    continue
                try:
                    size = entry.stat().st_size
                    if size >= min_size:
                        yield FileInfo(entry, size)
                except (PermissionError, OSError) as e:
                    logging.warning(f"Failed to inspect file {entry}: {e}")
    except (PermissionError, OSError) as e:
        logging.warning(f"Failed to scan for large files in {root}: {e}")


def find_space_hogs(root: Path, min_size_mb: int = 50) -> list[tuple[Path, int, str]]:
    """Find common space-hogging directories."""
    results = []
    min_size = min_size_mb * 1024 * 1024
    pattern_names = set(SPACE_HOG_PATTERNS.keys())

    def _walk_error(error: OSError):
        logging.warning(f"Skipping inaccessible path {getattr(error, 'filename', root)}: {error}")

    try:
        # Handle root itself if it matches a known hog pattern.
        if root.name in pattern_names and not root.is_symlink():
            try:
                size = get_dir_size(root)
                if size >= min_size:
                    results.append((root, size, SPACE_HOG_PATTERNS[root.name]))
            except (PermissionError, OSError) as e:
                logging.warning(f"Failed to size potential space hog {root}: {e}")

        for dirpath, dirnames, _ in os.walk(root, topdown=True, followlinks=False, onerror=_walk_error):
            # Prevent traversal into symlinked directories.
            dirnames[:] = [
                d for d in dirnames
                if not os.path.islink(os.path.join(dirpath, d))
            ]

            # Prune only matched hog directories so sibling branches are still walked.
            for dirname in list(dirnames):
                if dirname not in pattern_names:
                    continue
                current = Path(dirpath) / dirname
                try:
                    size = get_dir_size(current)
                    if size >= min_size:
                        results.append((current, size, SPACE_HOG_PATTERNS[dirname]))
                    dirnames.remove(dirname)
                except (PermissionError, OSError) as e:
                    logging.warning(f"Failed to size potential space hog {current}: {e}")
    except (PermissionError, OSError) as e:
        logging.warning(f"Failed to walk for space hogs in {root}: {e}")

    return sorted(results, key=lambda x: x[1], reverse=True)


def find_duplicates(root: Path, min_size_mb: int = 10) -> dict[str, list[Path]]:
    """Find duplicate files by comparing file sizes and hashes."""
    min_size = min_size_mb * 1024 * 1024

    # Group by size first
    size_groups = defaultdict(list)

    def _walk_error(error: OSError):
        logging.warning(f"Failed to scan path {getattr(error, 'filename', root)}: {error}")

    try:
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False, onerror=_walk_error):
            dirnames[:] = [
                d for d in dirnames
                if not os.path.islink(os.path.join(dirpath, d))
            ]
            for filename in filenames:
                entry = Path(dirpath) / filename
                if entry.is_symlink():
                    continue
                try:
                    size = entry.stat().st_size
                    if size >= min_size:
                        size_groups[size].append(entry)
                except (PermissionError, OSError) as e:
                    logging.warning(f"Failed to inspect file {entry}: {e}")
    except (PermissionError, OSError) as e:
        logging.warning(f"Failed to scan for duplicates in {root}: {e}")

    # For groups with same size, compute hash
    duplicates = defaultdict(list)
    for size, files in size_groups.items():
        if len(files) < 2:
            continue

        for filepath in files:
            try:
                file_hash = hash_file(filepath)
                duplicates[file_hash].append(filepath)
            except (PermissionError, OSError) as e:
                logging.warning(f"Failed to hash file {filepath}: {e}")

    # Filter to only actual duplicates
    return {h: files for h, files in duplicates.items() if len(files) > 1}


def hash_file(filepath: Path, chunk_size: int = 8192) -> str:
    """Compute MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()
