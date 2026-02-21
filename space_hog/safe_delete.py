"""Safe deletion utilities for Space Hog.

Moves files to Trash instead of permanent deletion, allowing recovery.
"""

import logging
import os
import shlex
import shutil
import stat
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


def _estimate_path_size(target: Path, target_stat: os.stat_result) -> int:
    """Estimate bytes represented by a target path without following symlinks."""
    if stat.S_ISREG(target_stat.st_mode):
        return target_stat.st_size
    if not stat.S_ISDIR(target_stat.st_mode):
        return 0

    total_size = 0

    def _walk_error(error: OSError):
        logging.warning(f"Failed to inspect {getattr(error, 'filename', target)}: {error}")

    for dirpath, dirnames, filenames in os.walk(target, topdown=True, followlinks=False, onerror=_walk_error):
        dirnames[:] = [
            d for d in dirnames
            if not os.path.islink(os.path.join(dirpath, d))
        ]
        for name in filenames:
            file_path = Path(dirpath) / name
            try:
                file_stat = file_path.lstat()
                if stat.S_ISREG(file_stat.st_mode):
                    total_size += file_stat.st_size
            except (PermissionError, OSError) as e:
                logging.warning(f"Failed to inspect file {file_path}: {e}")

    return total_size


def move_to_trash(path: str, dry_run: bool = False) -> dict:
    """Safely move a file or directory to Trash instead of deleting.

    Args:
        path: Path to file or directory to trash
        dry_run: If True, only show what would be done

    Returns:
        dict with 'success', 'message', 'bytes_freed' (estimated)
    """
    target = Path(path).expanduser()
    try:
        target_stat = target.lstat()
    except FileNotFoundError:
        return {
            'success': False,
            'message': f'Path does not exist: {path}',
            'bytes_freed': 0,
            'bytes_freed_human': format_size(0),
            'dry_run': dry_run,
        }
    except (PermissionError, OSError) as e:
        logging.warning(f"Failed to inspect target {target}: {e}")
        return {
            'success': False,
            'message': f'Failed to inspect path: {e}',
            'bytes_freed': 0,
            'bytes_freed_human': format_size(0),
            'dry_run': dry_run,
        }

    if stat.S_ISLNK(target_stat.st_mode):
        return {
            'success': False,
            'message': f'Refusing to trash symlink: {path}',
            'bytes_freed': 0,
            'bytes_freed_human': format_size(0),
            'dry_run': dry_run,
        }

    try:
        size = _estimate_path_size(target, target_stat)
    except Exception as e:
        logging.warning(f"Failed to calculate size for {target}: {e}")
        size = 0
    is_file = stat.S_ISREG(target_stat.st_mode)

    if dry_run:
        return {
            'success': True,
            'message': f'[DRY RUN] Would move to Trash: {path}',
            'bytes_freed': size,
            'bytes_freed_human': format_size(size),
            'dry_run': True,
        }

    try:
        try:
            if stat.S_ISLNK(target.lstat().st_mode):
                return {
                    'success': False,
                    'message': f'Refusing to trash symlink: {path}',
                    'bytes_freed': 0,
                    'bytes_freed_human': format_size(0),
                    'dry_run': False,
                }
        except FileNotFoundError:
            return {
                'success': False,
                'message': f'Path does not exist: {path}',
                'bytes_freed': 0,
                'bytes_freed_human': format_size(0),
                'dry_run': False,
            }

        if send2trash is None:
            return _fallback_trash(target, size, is_file)

        send2trash.send2trash(str(target))
        _record_removal(target.name, 'file' if is_file else 'directory', size)
        return {
            'success': True,
            'message': f'Moved to Trash: {path}',
            'bytes_freed': size,
            'bytes_freed_human': format_size(size),
            'dry_run': False,
            'recoverable': True,
        }
    except Exception as e:
        logging.warning(f"Failed to move {target} to Trash: {e}")
        return {
            'success': False,
            'message': f'Failed to trash: {e}',
            'bytes_freed': 0,
            'bytes_freed_human': format_size(0),
            'dry_run': False,
        }


def _fallback_trash(target: Path, size: int, is_file: bool) -> dict:
    """Fallback: manually move to ~/.Trash with timestamp to avoid conflicts."""
    trash_dir = Path.home() / '.Trash'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    trash_name = f"{target.name}_{timestamp}"
    trash_path = trash_dir / trash_name

    try:
        try:
            if stat.S_ISLNK(target.lstat().st_mode):
                return {
                    'success': False,
                    'message': f'Refusing to trash symlink: {target}',
                    'bytes_freed': 0,
                    'bytes_freed_human': format_size(0),
                    'dry_run': False,
                }
        except FileNotFoundError:
            return {
                'success': False,
                'message': f'Path does not exist: {target}',
                'bytes_freed': 0,
                'bytes_freed_human': format_size(0),
                'dry_run': False,
            }

        trash_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(trash_path))
        # Record the decision for learning
        _record_removal(target.name, 'file' if is_file else 'directory', size)
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
        logging.warning(f"Fallback trash move failed for {target}: {e}")
        return {
            'success': False,
            'message': f'Failed to move to Trash: {e}',
            'bytes_freed': 0,
            'bytes_freed_human': format_size(0),
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
        except Exception as e:
            logging.warning(f"Failed to record app removal decision: {e}")

    return result


def safe_cleanup(command: str, description: str, category: str = 'manual', dry_run: bool = False) -> dict:
    """Convert dangerous rm commands to safe Trash operations when possible.

    Args:
        command: The cleanup command (may be rm -rf or other)
        description: Human-readable description
        category: Cleanup category for stats tracking
        dry_run: If True, only show what would be done

    Returns:
        dict with cleanup results
    """
    from .stats import record_cleanup, run_cleanup

    try:
        tokens = shlex.split(command)
    except ValueError as e:
        logging.warning(f"Failed to parse cleanup command '{command}': {e}")
        return {
            'success': False,
            'bytes_freed': 0,
            'bytes_freed_human': format_size(0),
            'error': str(e),
            'command': command,
            'recorded': False,
        }

    if not tokens:
        return {
            'success': False,
            'bytes_freed': 0,
            'bytes_freed_human': format_size(0),
            'error': 'Empty command',
            'command': command,
            'recorded': False,
        }

    if tokens[0] != 'rm':
        if dry_run:
            return {
                'success': True,
                'message': f'[DRY RUN] Would run: {command}',
                'bytes_freed': 0,
                'bytes_freed_human': format_size(0),
                'dry_run': True,
                'recoverable': False,
                'note': 'This command cannot be converted to a Trash operation',
                'error': None,
                'command': command,
                'recorded': False,
            }
        return run_cleanup(command, description, category)

    targets: list[str] = []
    force_mode = False
    parsing_options = True
    for token in tokens[1:]:
        if parsing_options and token == '--':
            parsing_options = False
            continue
        if parsing_options and token.startswith('-'):
            option_flags = token.lstrip('-')
            if 'f' in option_flags:
                force_mode = True
            continue
        targets.append(token)

    if not targets:
        return {
            'success': False,
            'bytes_freed': 0,
            'bytes_freed_human': format_size(0),
            'error': 'No rm targets provided',
            'command': command,
            'recorded': False,
        }

    total_size = 0
    recoverable = True
    had_errors = False
    error_messages: list[str] = []

    def _is_missing_path_message(message: str | None) -> bool:
        if not message:
            return False
        return (
            message.startswith('Path does not exist:')
            or message.startswith('Directory does not exist:')
        )

    def _expand_target(token: str) -> list[str]:
        expanded = str(Path(token).expanduser()) if token.startswith('~') else token
        if any(ch in expanded for ch in ['*', '?', '[']):
            import glob
            return glob.glob(expanded)
        return [expanded]

    for token in targets:
        expanded_token = str(Path(token).expanduser()) if token.startswith('~') else token

        if expanded_token.endswith('/*') and not any(ch in expanded_token[:-2] for ch in ['*', '?', '[']):
            dir_path = expanded_token[:-2]
            result = trash_contents(dir_path, dry_run=dry_run)
            total_size += result.get('bytes_freed', 0)
            if not result.get('success', False):
                if force_mode and _is_missing_path_message(result.get('message')):
                    continue
                had_errors = True
                if result.get('message'):
                    error_messages.append(result['message'])
                if result.get('errors'):
                    error_messages.extend(result['errors'])
            continue

        expanded_targets = _expand_target(token)
        for resolved in expanded_targets:
            result = move_to_trash(resolved, dry_run=dry_run)
            total_size += result.get('bytes_freed', 0)
            if not result.get('success', False):
                if force_mode and _is_missing_path_message(result.get('message')):
                    continue
                had_errors = True
                if result.get('message'):
                    error_messages.append(result['message'])

        if any(ch in expanded_token for ch in ['*', '?', '[']) and not expanded_targets:
            logging.warning(f"Cleanup glob had no matches: {expanded_token}")

    success = not had_errors
    if not dry_run and success and total_size > 0:
        record_cleanup(description, total_size, category)

    return {
        'success': success,
        'bytes_freed': total_size,
        'bytes_freed_human': format_size(total_size),
        'error': None if success else '; '.join(error_messages) if error_messages else 'Cleanup failed',
        'command': command,
        'recorded': (not dry_run and success and total_size > 0),
        'dry_run': dry_run,
        'recoverable': recoverable,
    }
