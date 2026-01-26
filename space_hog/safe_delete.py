"""Safe deletion utilities for Space Hog.

Moves files to Trash instead of permanent deletion, allowing recovery.
"""

import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from .utils import format_size


def move_to_trash(path: str, dry_run: bool = False) -> dict:
    """Safely move a file or directory to Trash instead of deleting.

    Args:
        path: Path to file or directory to trash
        dry_run: If True, only show what would be done

    Returns:
        dict with 'success', 'message', 'bytes_freed' (estimated)
    """
    target = Path(path).expanduser()

    if not target.exists():
        return {
            'success': False,
            'message': f'Path does not exist: {path}',
            'bytes_freed': 0,
            'dry_run': dry_run,
        }

    # Calculate size before moving
    try:
        if target.is_file():
            size = target.stat().st_size
        else:
            size = sum(f.stat().st_size for f in target.rglob('*') if f.is_file())
    except (PermissionError, OSError):
        size = 0

    if dry_run:
        return {
            'success': True,
            'message': f'[DRY RUN] Would move to Trash: {path}',
            'bytes_freed': size,
            'bytes_freed_human': format_size(size),
            'dry_run': True,
        }

    # Use macOS Finder to move to Trash (proper Trash behavior with undo support)
    try:
        # AppleScript approach - proper Trash with "Put Back" support
        script = f'''
        tell application "Finder"
            delete POSIX file "{target}"
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return {
                'success': True,
                'message': f'Moved to Trash: {path}',
                'bytes_freed': size,
                'bytes_freed_human': format_size(size),
                'dry_run': False,
                'recoverable': True,
            }
        else:
            # Fallback: manual move to ~/.Trash
            return _fallback_trash(target, size)

    except subprocess.TimeoutExpired:
        return _fallback_trash(target, size)
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to trash: {e}',
            'bytes_freed': 0,
            'dry_run': False,
        }


def _fallback_trash(target: Path, size: int) -> dict:
    """Fallback: manually move to ~/.Trash with timestamp to avoid conflicts."""
    trash_dir = Path.home() / '.Trash'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    trash_name = f"{target.name}_{timestamp}"
    trash_path = trash_dir / trash_name

    try:
        shutil.move(str(target), str(trash_path))
        return {
            'success': True,
            'message': f'Moved to Trash: {target.name} (as {trash_name})',
            'bytes_freed': size,
            'bytes_freed_human': format_size(size),
            'dry_run': False,
            'recoverable': True,
            'trash_path': str(trash_path),
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to move to Trash: {e}',
            'bytes_freed': 0,
            'dry_run': False,
        }


def trash_contents(directory: str, dry_run: bool = False) -> dict:
    """Move all contents of a directory to Trash, keeping the directory itself.

    Safer alternative to `rm -rf directory/*`

    Args:
        directory: Directory whose contents should be trashed
        dry_run: If True, only show what would be done
    """
    target = Path(directory).expanduser()

    if not target.exists():
        return {
            'success': False,
            'message': f'Directory does not exist: {directory}',
            'bytes_freed': 0,
            'items_trashed': 0,
            'dry_run': dry_run,
        }

    if not target.is_dir():
        return {
            'success': False,
            'message': f'Not a directory: {directory}',
            'bytes_freed': 0,
            'items_trashed': 0,
            'dry_run': dry_run,
        }

    total_size = 0
    items_trashed = 0
    errors = []

    try:
        items = list(target.iterdir())
    except PermissionError:
        return {
            'success': False,
            'message': f'Permission denied: {directory}',
            'bytes_freed': 0,
            'items_trashed': 0,
            'dry_run': dry_run,
        }

    for item in items:
        result = move_to_trash(str(item), dry_run=dry_run)
        if result['success']:
            total_size += result.get('bytes_freed', 0)
            items_trashed += 1
        else:
            errors.append(result['message'])

    prefix = '[DRY RUN] ' if dry_run else ''
    return {
        'success': len(errors) == 0,
        'message': f'{prefix}Trashed {items_trashed} items from {directory}',
        'bytes_freed': total_size,
        'bytes_freed_human': format_size(total_size),
        'items_trashed': items_trashed,
        'errors': errors if errors else None,
        'dry_run': dry_run,
        'recoverable': True,
    }


def safe_cleanup(command: str, description: str, dry_run: bool = False) -> dict:
    """Convert dangerous rm commands to safe Trash operations when possible.

    Args:
        command: The cleanup command (may be rm -rf or other)
        description: Human-readable description
        dry_run: If True, only show what would be done

    Returns:
        dict with cleanup results
    """
    # Parse common rm -rf patterns and convert to safe operations
    import re

    # Pattern: rm -rf ~/path/* or rm -rf /path/*
    match = re.match(r'^rm\s+-rf?\s+([~\w/\\\s.-]+)/\*\s*$', command)
    if match:
        path = match.group(1).strip()
        return trash_contents(path, dry_run=dry_run)

    # Pattern: rm -rf ~/path or rm -rf /path (whole directory)
    match = re.match(r'^rm\s+-rf?\s+([~\w/\\\s.-]+)\s*$', command)
    if match:
        path = match.group(1).strip()
        return move_to_trash(path, dry_run=dry_run)

    # For non-rm commands (npm cache clean, docker prune, etc.),
    # we can't safely intercept - just report what would happen
    if dry_run:
        return {
            'success': True,
            'message': f'[DRY RUN] Would run: {command}',
            'bytes_freed': 0,
            'dry_run': True,
            'recoverable': False,
            'note': 'This command cannot be converted to a Trash operation',
        }

    # For actual execution of non-rm commands, use the original run_cleanup
    from .stats import run_cleanup
    return run_cleanup(command, description)
