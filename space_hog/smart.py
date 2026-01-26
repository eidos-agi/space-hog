"""Smart cleanup detection for Space Hog.

Finds waste that requires pattern analysis, not just scanning known paths.
Inspired by CleanMyMac's intelligent categorization.
"""

import subprocess
from pathlib import Path
from typing import Generator

from .utils import format_size, get_dir_size


def find_dmg_files(min_size_mb: int = 10) -> list[dict]:
    """Find DMG installer files in Downloads and Desktop.

    DMGs are often left behind after installing apps.
    """
    results = []
    min_bytes = min_size_mb * 1024 * 1024

    search_paths = [
        Path.home() / 'Downloads',
        Path.home() / 'Desktop',
    ]

    for search_path in search_paths:
        if not search_path.exists():
            continue

        for dmg in search_path.glob('*.dmg'):
            try:
                size = dmg.stat().st_size
                if size >= min_bytes:
                    results.append({
                        'path': str(dmg),
                        'name': dmg.name,
                        'size': size,
                        'size_human': format_size(size),
                        'location': search_path.name,
                    })
            except (PermissionError, OSError):
                pass

    return sorted(results, key=lambda x: x['size'], reverse=True)


def find_old_downloads(days: int = 90, min_size_mb: int = 50) -> list[dict]:
    """Find old files in Downloads folder.

    Files untouched for 90+ days are likely forgotten.
    """
    import time

    results = []
    downloads = Path.home() / 'Downloads'
    min_bytes = min_size_mb * 1024 * 1024
    cutoff = time.time() - (days * 24 * 60 * 60)

    if not downloads.exists():
        return results

    for item in downloads.iterdir():
        try:
            stat = item.stat()
            # Check both mtime and atime
            last_access = max(stat.st_mtime, stat.st_atime)

            if last_access < cutoff:
                if item.is_file():
                    size = stat.st_size
                elif item.is_dir():
                    size = get_dir_size(item)
                else:
                    continue

                if size >= min_bytes:
                    results.append({
                        'path': str(item),
                        'name': item.name,
                        'size': size,
                        'size_human': format_size(size),
                        'is_dir': item.is_dir(),
                        'days_old': int((time.time() - last_access) / 86400),
                    })
        except (PermissionError, OSError):
            pass

    return sorted(results, key=lambda x: x['size'], reverse=True)


def find_localization_files() -> dict:
    """Find unused language localization files in apps.

    Most apps include 20+ language files you'll never use.
    Can save 1-3 GB system-wide.
    """
    # Get system language
    try:
        result = subprocess.run(
            ['defaults', 'read', '-g', 'AppleLanguages'],
            capture_output=True, text=True, timeout=5
        )
        # Parse the output to get primary language
        # Format is like: (\n    "en-US",\n    "fr-FR"\n)
        lines = result.stdout.strip().split('\n')
        primary_lang = None
        for line in lines:
            line = line.strip().strip(',').strip('"')
            if line and not line.startswith('(') and not line.startswith(')'):
                primary_lang = line.split('-')[0]  # "en-US" -> "en"
                break
    except Exception:
        primary_lang = 'en'

    total_size = 0
    app_count = 0

    apps_path = Path('/Applications')
    if not apps_path.exists():
        return {'total_size': 0, 'app_count': 0, 'primary_language': primary_lang}

    for app in apps_path.glob('*.app'):
        resources = app / 'Contents' / 'Resources'
        if not resources.exists():
            continue

        for lproj in resources.glob('*.lproj'):
            lang_code = lproj.stem.lower()
            # Skip if it's the user's language or Base (required)
            if lang_code in (primary_lang.lower(), 'base', 'en'):
                continue
            try:
                size = get_dir_size(lproj)
                total_size += size
                app_count += 1
            except (PermissionError, OSError):
                pass

    return {
        'total_size': total_size,
        'total_size_human': format_size(total_size),
        'app_count': app_count,
        'primary_language': primary_lang,
        'note': 'Removing requires tools like monolingual.app (risky for system apps)',
    }


def find_time_machine_snapshots() -> dict:
    """Check for local Time Machine snapshots.

    macOS keeps local snapshots that can use 10-100+ GB.
    """
    try:
        result = subprocess.run(
            ['tmutil', 'listlocalsnapshots', '/'],
            capture_output=True, text=True, timeout=10
        )
        snapshots = [
            line for line in result.stdout.strip().split('\n')
            if line and not line.startswith('Snapshots')
        ]

        # Get estimated size (this is approximate)
        # Each snapshot can be 1-50 GB depending on changes
        snapshot_count = len(snapshots)

        return {
            'snapshot_count': snapshot_count,
            'snapshots': snapshots[:10],  # First 10
            'estimated_size': snapshot_count * 5 * 1024 * 1024 * 1024,  # ~5GB each estimate
            'estimated_size_human': format_size(snapshot_count * 5 * 1024 * 1024 * 1024),
            'command': 'sudo tmutil deletelocalsnapshots <date>',
            'note': 'macOS manages these automatically. Delete only if desperate for space.',
        }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {'snapshot_count': 0, 'snapshots': [], 'note': 'Time Machine not available'}


def find_broken_symlinks(search_paths: list[str] = None) -> list[dict]:
    """Find broken symbolic links.

    Broken symlinks waste space and cause confusion.
    """
    if search_paths is None:
        search_paths = [
            str(Path.home()),
            '/usr/local',
        ]

    broken = []

    for search_path in search_paths:
        path = Path(search_path)
        if not path.exists():
            continue

        try:
            # Use find command for speed
            result = subprocess.run(
                ['find', str(path), '-maxdepth', '3', '-type', 'l', '-not', '-exec', 'test', '-e', '{}', ';', '-print'],
                capture_output=True, text=True, timeout=30
            )
            for line in result.stdout.strip().split('\n'):
                if line:
                    broken.append({
                        'path': line,
                        'target': str(Path(line).resolve()) if Path(line).is_symlink() else 'unknown',
                    })
        except (subprocess.TimeoutExpired, Exception):
            pass

    return broken[:50]  # Limit to 50


def get_smart_recommendations() -> dict:
    """Get all smart cleanup recommendations."""
    dmgs = find_dmg_files()
    old_downloads = find_old_downloads()
    localization = find_localization_files()
    snapshots = find_time_machine_snapshots()

    total_dmg_size = sum(d['size'] for d in dmgs)
    total_downloads_size = sum(d['size'] for d in old_downloads)

    return {
        'dmg_installers': {
            'items': dmgs,
            'count': len(dmgs),
            'total_size': total_dmg_size,
            'total_size_human': format_size(total_dmg_size),
            'risk': 'SAFE',
            'description': 'DMG installer files left in Downloads/Desktop after installing apps.',
        },
        'old_downloads': {
            'items': old_downloads,
            'count': len(old_downloads),
            'total_size': total_downloads_size,
            'total_size_human': format_size(total_downloads_size),
            'risk': 'MODERATE',
            'description': 'Files in Downloads untouched for 90+ days.',
        },
        'localization': localization,
        'time_machine_snapshots': snapshots,
    }
