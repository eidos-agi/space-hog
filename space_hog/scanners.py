"""File system scanners for Space Hog."""

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Generator

from .utils import FileInfo, get_dir_size
from .constants import SPACE_HOG_PATTERNS


def find_large_files(root: Path, min_size_mb: int = 100) -> Generator[FileInfo, None, None]:
    """Find files larger than min_size_mb."""
    min_size = min_size_mb * 1024 * 1024
    try:
        for entry in root.rglob('*'):
            if entry.is_file() and not entry.is_symlink():
                try:
                    size = entry.stat().st_size
                    if size >= min_size:
                        yield FileInfo(entry, size)
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass


def find_space_hogs(root: Path, min_size_mb: int = 50) -> list[tuple[Path, int, str]]:
    """Find common space-hogging directories using a single optimized pass."""
    import os
    results = []
    min_size = min_size_mb * 1024 * 1024
    
    # Pre-compile the targets for fast lookup
    target_names = set(SPACE_HOG_PATTERNS.keys())

    try:
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip symlinks to avoid infinite loops and arbitrary reads
            if os.path.islink(dirpath):
                continue
                
            # Iterate over a copy of dirnames so we can modify the list to prevent descending
            for dirname in list(dirnames):
                full_path = Path(dirpath) / dirname
                
                if os.path.islink(full_path):
                    continue
                    
                if dirname in target_names:
                    try:
                        size = get_dir_size(full_path)
                        if size >= min_size:
                            results.append((full_path, size, SPACE_HOG_PATTERNS[dirname]))
                    except (PermissionError, OSError):
                        pass
                    # Don't descend into space hogs (e.g. don't look for .git inside node_modules)
                    dirnames.remove(dirname)
    except (PermissionError, OSError):
        pass

    return sorted(results, key=lambda x: x[1], reverse=True)


def find_duplicates(root: Path, min_size_mb: int = 10) -> dict[str, list[Path]]:
    """Find duplicate files by comparing file sizes and hashes."""
    min_size = min_size_mb * 1024 * 1024

    # Group by size first
    size_groups = defaultdict(list)
    try:
        for entry in root.rglob('*'):
            if entry.is_file() and not entry.is_symlink():
                try:
                    size = entry.stat().st_size
                    if size >= min_size:
                        size_groups[size].append(entry)
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass

    # For groups with same size, compute hash
    duplicates = defaultdict(list)
    for size, files in size_groups.items():
        if len(files) < 2:
            continue

        for filepath in files:
            try:
                file_hash = hash_file(filepath)
                duplicates[file_hash].append(filepath)
            except (PermissionError, OSError):
                pass

    # Filter to only actual duplicates
    return {h: files for h, files in duplicates.items() if len(files) > 1}


def hash_file(filepath: Path, chunk_size: int = 8192) -> str:
    """Compute MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()
