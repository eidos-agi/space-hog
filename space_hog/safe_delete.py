"""Safe deletion utilities for Space Hog.

Moves files to Trash instead of permanent deletion, allowing recovery.
"""

import shutil
import logging
from pathlib import Path
from datetime import datetime

try:
    import send2trash
except ImportError:  # pragma: no cover - dependency declared in pyproject.toml
    send2trash = None

from .utils import format_size


def _record_removal(item_name: str, item_type: str, size_bytes: int):
    """Record a removal decision for learning preferences."""
    try:
        from .preferences import record_decision
        record_decision(item_type, item_name, 'removed', size_bytes)
    except Exception as e:
        logging.warning(f"Failed to record removal: {e}")


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

    try:
        if send2trash is None:
            return _fallback_trash(target, size)

        send2trash.send2trash(str(target))
        _record_removal(target.name, 'file' if target.is_file() else 'directory', size)
        return {
            'success': True,
            'message': f'Moved to Trash: {path}',
            'bytes_freed': size,
            'bytes_freed_human': format_size(size),
            'dry_run': False,
            'recoverable': True,
        }
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
        # Record the decision for learning
        _record_removal(target.name, 'file' if target.is_file() else 'directory', size)
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
        if item.is_symlink():
            errors.append(f'Skipped symlink: {item}')
            continue
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


def trash_app(app_name: str, dry_run: bool = False) -> dict:
    """Move an application to Trash and record the decision.

    Args:
        app_name: Name of the app (e.g., "Inkscape" or "Inkscape.app")
        dry_run: If True, only show what would be done

    Returns:
        dict with result info
    """
    # Normalize app name
    if not app_name.endswith('.app'):
        app_name = f"{app_name}.app"

    app_path = Path('/Applications') / app_name

    if not app_path.exists():
        # Try user Applications folder
        app_path = Path.home() / 'Applications' / app_name

    if not app_path.exists():
        return {
            'success': False,
            'message': f'App not found: {app_name}',
            'bytes_freed': 0,
            'dry_run': dry_run,
        }

    result = move_to_trash(str(app_path), dry_run=dry_run)

    # Record as an app removal specifically (for learning)
    if result['success'] and not dry_run:
        try:
            from .preferences import record_decision
            record_decision('app', app_name.replace('.app', ''), 'removed', result.get('bytes_freed', 0))
        except Exception:
            pass

    return result


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
