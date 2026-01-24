#!/usr/bin/env python3
"""
Space Hog - Find wasted space on your Mac

A CLI tool that identifies large files, caches, duplicates, and cleanup opportunities.
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Generator
import subprocess


@dataclass
class FileInfo:
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


# Common space hogs on macOS
SPACE_HOG_PATTERNS = {
    'node_modules': 'Node.js dependencies',
    '.git': 'Git repositories',
    '__pycache__': 'Python cache',
    '.pytest_cache': 'Pytest cache',
    'venv': 'Python virtual environments',
    '.venv': 'Python virtual environments',
    'env': 'Python virtual environments',
    '.tox': 'Tox testing environments',
    'target': 'Rust/Maven build artifacts',
    'build': 'Build directories',
    'dist': 'Distribution directories',
    '.gradle': 'Gradle cache',
    '.cargo': 'Cargo cache',
    'Pods': 'CocoaPods dependencies',
    'DerivedData': 'Xcode derived data',
    '.nuget': 'NuGet packages',
    'vendor': 'Vendor dependencies',
}

CACHE_LOCATIONS = [
    ('~/Library/Caches', 'Application caches'),
    ('~/Library/Application Support/Code/Cache', 'VS Code cache'),
    ('~/Library/Application Support/Code/CachedData', 'VS Code cached data'),
    ('~/Library/Application Support/Slack/Cache', 'Slack cache'),
    ('~/Library/Application Support/discord/Cache', 'Discord cache'),
    ('~/Library/Application Support/Google/Chrome/Default/Cache', 'Chrome cache'),
    ('~/Library/Developer/Xcode/DerivedData', 'Xcode derived data'),
    ('~/Library/Developer/Xcode/Archives', 'Xcode archives'),
    ('~/Library/Developer/CoreSimulator', 'iOS Simulators'),
    ('~/.npm', 'NPM cache'),
    ('~/.yarn/cache', 'Yarn cache'),
    ('~/.cache', 'General cache'),
    ('~/.docker', 'Docker data'),
    ('~/Library/Containers/com.docker.docker', 'Docker Desktop'),
]

# Cleanup commands with safety information
# Format: (command, risk_level, description, side_effects, recommendation)
CLEANUP_COMMANDS = [
    {
        'command': 'rm -rf ~/.Trash/*',
        'name': 'Empty Trash',
        'risk': 'SAFE',
        'description': 'Permanently deletes files already in your Trash.',
        'side_effects': [
            'Files cannot be recovered after this',
        ],
        'recommendation': 'Safe to run. Review Trash contents first if unsure.',
    },
    {
        'command': 'npm cache clean --force',
        'name': 'Clear NPM Cache',
        'risk': 'SAFE',
        'description': 'Removes cached npm packages. NPM self-heals since v5.',
        'side_effects': [
            'Next npm install will re-download packages (slightly slower)',
            'No impact on installed node_modules',
        ],
        'recommendation': 'Safe to run. Try "npm cache verify" first for a gentler approach.',
    },
    {
        'command': 'docker system prune -a',
        'name': 'Clear Docker',
        'risk': 'MODERATE',
        'description': 'Removes stopped containers, unused networks, and ALL unused images.',
        'side_effects': [
            'Must re-pull/rebuild images not currently in use',
            'Build cache cleared (slower first builds)',
            'Does NOT delete volumes (data is safe)',
        ],
        'recommendation': 'Safe for dev machines. Use "docker system prune" (no -a) to keep tagged images.',
    },
    {
        'command': 'rm -rf ~/Library/Caches/*',
        'name': 'Clear User Caches',
        'risk': 'SAFE',
        'description': 'Removes application cache files. macOS regenerates them automatically.',
        'side_effects': [
            'Apps may be slower on first launch while rebuilding cache',
            'May need to re-login to some apps',
            'Some apps store non-cache data here (rare)',
        ],
        'recommendation': 'Generally safe. Consider backing up first if concerned.',
    },
    {
        'command': 'rm -rf ~/.cache/*',
        'name': 'Clear ~/.cache',
        'risk': 'SAFE',
        'description': 'Removes general cache directory used by CLI tools and apps.',
        'side_effects': [
            'Tools rebuild caches on next use',
            'May need to re-authenticate some CLI tools',
        ],
        'recommendation': 'Safe to run. Data regenerates automatically.',
    },
    {
        'command': 'xcrun simctl delete unavailable',
        'name': 'Delete Unavailable iOS Simulators',
        'risk': 'SAFE',
        'description': 'Removes simulators incompatible with current Xcode version.',
        'side_effects': [
            'Only removes simulators you cannot use anyway',
        ],
        'recommendation': 'Safe to run. Also try "xcrun simctl runtime delete unavailable" for runtimes.',
    },
    {
        'command': 'rm -rf ~/Library/Developer/Xcode/DerivedData/*',
        'name': 'Clear Xcode DerivedData',
        'risk': 'SAFE',
        'description': 'Removes Xcode build artifacts and indexes.',
        'side_effects': [
            'Next build will be slower (full rebuild)',
            'Xcode will re-index projects',
        ],
        'recommendation': 'Safe to run. Common fix for Xcode build issues.',
    },
    {
        'command': 'yarn cache clean',
        'name': 'Clear Yarn Cache',
        'risk': 'SAFE',
        'description': 'Removes cached yarn packages.',
        'side_effects': [
            'Next yarn install will re-download packages',
        ],
        'recommendation': 'Safe to run.',
    },
]


def find_space_hogs(root: Path, min_size_mb: int = 50) -> list[tuple[Path, int, str]]:
    """Find common space-hogging directories."""
    results = []
    min_size = min_size_mb * 1024 * 1024

    for pattern, description in SPACE_HOG_PATTERNS.items():
        try:
            for entry in root.rglob(pattern):
                if entry.is_dir():
                    try:
                        size = get_dir_size(entry)
                        if size >= min_size:
                            results.append((entry, size, description))
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass

    return sorted(results, key=lambda x: x[1], reverse=True)


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

    import time
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


def print_header(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_cleanup_guide():
    """Print detailed cleanup guide with safety information."""
    print_header("CLEANUP GUIDE")
    print("  Each command includes risk level and side effects.\n")

    for cmd in CLEANUP_COMMANDS:
        risk_color = {
            'SAFE': '\033[92m',      # Green
            'MODERATE': '\033[93m',  # Yellow
            'CAUTION': '\033[91m',   # Red
        }.get(cmd['risk'], '')
        reset = '\033[0m'

        print(f"  {'-'*56}")
        print(f"  {cmd['name']}")
        print(f"  Risk: {risk_color}{cmd['risk']}{reset}")
        print(f"  Command: {cmd['command']}")
        print()
        print(f"  What it does:")
        print(f"    {cmd['description']}")
        print()
        print(f"  Side effects:")
        for effect in cmd['side_effects']:
            print(f"    - {effect}")
        print()
        print(f"  Recommendation:")
        print(f"    {cmd['recommendation']}")
        print()

    print(f"  {'-'*56}")
    print()
    print("  RISK LEVELS:")
    print("    SAFE     - No meaningful downside, data regenerates")
    print("    MODERATE - Some rebuild time or re-download needed")
    print("    CAUTION  - Review before running, potential data impact")
    print()


def scan_all(root: Path, args):
    """Run all scans and display results."""
    total_reclaimable = 0

    # Trash
    print_header("TRASH")
    trash_size = get_trash_size()
    if trash_size > 0:
        print(f"  Trash: {format_size(trash_size)}")
        print(f"  Clean with: rm -rf ~/.Trash/*")
        total_reclaimable += trash_size
    else:
        print("  Trash is empty")

    # Downloads
    print_header("DOWNLOADS (files older than 30 days)")
    downloads_size, old_downloads = get_downloads_analysis()
    if downloads_size > 0:
        print(f"  Total old files: {format_size(downloads_size)} ({len(old_downloads)} files)")
        for f in old_downloads[:5]:
            print(f"    {f.size_human:>10}  {f.path.name}")
        if len(old_downloads) > 5:
            print(f"    ... and {len(old_downloads) - 5} more files")
        total_reclaimable += downloads_size
    else:
        print("  No old files in Downloads")

    # Caches
    print_header("CACHES")
    caches = check_caches()
    cache_total = sum(c[1] for c in caches)
    if caches:
        for path, size, desc in caches[:10]:
            print(f"  {format_size(size):>10}  {desc}")
            print(f"             {path}")
        if len(caches) > 10:
            print(f"  ... and {len(caches) - 10} more cache locations")
        print(f"\n  Total cache size: {format_size(cache_total)}")
        total_reclaimable += cache_total
    else:
        print("  No significant caches found")

    # Space hogs in specified directory
    print_header(f"SPACE HOGS IN {root}")
    hogs = find_space_hogs(root, min_size_mb=args.min_size)
    hog_total = sum(h[1] for h in hogs)
    if hogs:
        for path, size, desc in hogs[:15]:
            print(f"  {format_size(size):>10}  {desc}")
            print(f"             {path}")
        if len(hogs) > 15:
            print(f"  ... and {len(hogs) - 15} more directories")
        print(f"\n  Total: {format_size(hog_total)}")
        total_reclaimable += hog_total
    else:
        print(f"  No space hogs found (>{args.min_size}MB)")

    # Large files
    print_header(f"LARGE FILES (>{args.min_size}MB)")
    large_files = list(find_large_files(root, min_size_mb=args.min_size))
    large_files.sort(key=lambda x: x.size, reverse=True)
    if large_files:
        for f in large_files[:15]:
            print(f"  {f.size_human:>10}  {f.path}")
        if len(large_files) > 15:
            print(f"  ... and {len(large_files) - 15} more files")
    else:
        print(f"  No files found larger than {args.min_size}MB")

    # Duplicates (optional, can be slow)
    if args.duplicates:
        print_header("DUPLICATE FILES")
        print("  Scanning for duplicates (this may take a while)...")
        duplicates = find_duplicates(root, min_size_mb=args.min_size)
        if duplicates:
            dup_total = 0
            for file_hash, files in list(duplicates.items())[:10]:
                size = files[0].stat().st_size
                wasted = size * (len(files) - 1)
                dup_total += wasted
                print(f"\n  {format_size(size)} x {len(files)} copies ({format_size(wasted)} wasted):")
                for f in files[:3]:
                    print(f"    {f}")
                if len(files) > 3:
                    print(f"    ... and {len(files) - 3} more")
            print(f"\n  Total wasted by duplicates: {format_size(dup_total)}")
            total_reclaimable += dup_total
        else:
            print(f"  No duplicates found (>{args.min_size}MB)")

    # Summary
    print_header("SUMMARY")
    print(f"  Potentially reclaimable space: {format_size(total_reclaimable)}")
    print()
    print("  Run 'space-hog --cleanup-guide' for detailed cleanup instructions.")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Space Hog - Find wasted space on your Mac',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  space-hog                     # Scan home directory
  space-hog /path/to/scan       # Scan specific directory
  space-hog --min-size 50       # Only show items > 50MB
  space-hog --duplicates        # Include duplicate file scan
  space-hog --caches-only       # Only check cache locations
        """
    )
    parser.add_argument('path', nargs='?', default=str(Path.home()),
                        help='Directory to scan (default: home directory)')
    parser.add_argument('--min-size', type=int, default=100,
                        help='Minimum size in MB to report (default: 100)')
    parser.add_argument('--duplicates', '-d', action='store_true',
                        help='Scan for duplicate files (slower)')
    parser.add_argument('--caches-only', '-c', action='store_true',
                        help='Only check cache locations')
    parser.add_argument('--large-files', '-l', action='store_true',
                        help='Only find large files')
    parser.add_argument('--hogs-only', '-g', action='store_true',
                        help='Only find space hog directories')
    parser.add_argument('--cleanup-guide', action='store_true',
                        help='Show detailed cleanup guide with safety info')

    args = parser.parse_args()

    if args.cleanup_guide:
        print("\nSpace Hog - Cleanup Guide")
        print_cleanup_guide()
        sys.exit(0)
    root = Path(args.path).expanduser().resolve()

    if not root.exists():
        print(f"Error: Path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    print(f"\nSpace Hog - Scanning for wasted space...")
    print(f"Root: {root}")

    if args.caches_only:
        print_header("CACHES")
        caches = check_caches()
        for path, size, desc in caches:
            print(f"  {format_size(size):>10}  {desc}")
            print(f"             {path}")
        print(f"\n  Total: {format_size(sum(c[1] for c in caches))}")
    elif args.large_files:
        print_header(f"LARGE FILES (>{args.min_size}MB)")
        large_files = list(find_large_files(root, min_size_mb=args.min_size))
        large_files.sort(key=lambda x: x.size, reverse=True)
        for f in large_files:
            print(f"  {f.size_human:>10}  {f.path}")
    elif args.hogs_only:
        print_header(f"SPACE HOGS (>{args.min_size}MB)")
        hogs = find_space_hogs(root, min_size_mb=args.min_size)
        for path, size, desc in hogs:
            print(f"  {format_size(size):>10}  {desc}")
            print(f"             {path}")
    else:
        scan_all(root, args)


if __name__ == '__main__':
    main()
