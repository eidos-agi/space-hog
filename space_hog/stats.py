"""Statistics tracking for Space Hog.

Tracks disk space before/after cleanups and maintains history.
"""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import format_size


STATS_FILE = Path.home() / '.space-hog-stats.json'


def get_disk_usage() -> dict:
    """Get current disk usage for the main volume."""
    total, used, free = shutil.disk_usage("/")
    return {
        'total': total,
        'used': used,
        'free': free,
        'timestamp': datetime.now().isoformat(),
    }


def load_stats() -> dict:
    """Load stats from file."""
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {
        'cleanups': [],
        'total_saved': 0,
        'first_run': None,
    }


def save_stats(stats: dict):
    """Save stats to file."""
    STATS_FILE.write_text(json.dumps(stats, indent=2))


def record_cleanup(description: str, bytes_freed: int, category: str = 'manual'):
    """Record a cleanup action. Only use if you've verified the cleanup worked."""
    if bytes_freed <= 0:
        return None  # Don't record zero or negative savings

    stats = load_stats()

    if not stats['first_run']:
        stats['first_run'] = datetime.now().isoformat()

    cleanup_record = {
        'timestamp': datetime.now().isoformat(),
        'description': description,
        'bytes_freed': bytes_freed,
        'category': category,
        'disk_free_after': shutil.disk_usage("/").free,
        'verified': True,
    }

    stats['cleanups'].append(cleanup_record)
    stats['total_saved'] += bytes_freed

    save_stats(stats)
    return cleanup_record


def run_cleanup(command: str, description: str, category: str = 'manual') -> dict:
    """Run a cleanup command and measure actual space freed.

    This is the CORRECT way to run cleanups - it measures before/after
    and only records verified savings.

    Returns:
        dict with 'success', 'bytes_freed', 'bytes_freed_human', 'error'
    """
    from .utils import format_size

    # Measure before
    free_before = shutil.disk_usage("/").free

    # Run the command
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        success = result.returncode == 0 or 'no matches found' in result.stderr
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'bytes_freed': 0,
            'bytes_freed_human': '0 B',
            'error': 'Command timed out',
            'command': command,
        }
    except Exception as e:
        return {
            'success': False,
            'bytes_freed': 0,
            'bytes_freed_human': '0 B',
            'error': str(e),
            'command': command,
        }

    # Measure after
    free_after = shutil.disk_usage("/").free
    bytes_freed = free_after - free_before

    # Only record if we actually freed space
    if bytes_freed > 0:
        record_cleanup(description, bytes_freed, category)

    return {
        'success': success,
        'bytes_freed': max(0, bytes_freed),
        'bytes_freed_human': format_size(max(0, bytes_freed)),
        'error': None if success else result.stderr,
        'command': command,
        'recorded': bytes_freed > 0,
    }


def get_summary() -> dict:
    """Get summary of all cleanup activity."""
    stats = load_stats()

    if not stats['cleanups']:
        return {
            'total_cleanups': 0,
            'total_saved': 0,
            'total_saved_human': '0 B',
            'first_run': None,
            'last_cleanup': None,
            'by_category': {},
        }

    # Group by category
    by_category = {}
    for cleanup in stats['cleanups']:
        cat = cleanup.get('category', 'manual')
        if cat not in by_category:
            by_category[cat] = {'count': 0, 'bytes': 0}
        by_category[cat]['count'] += 1
        by_category[cat]['bytes'] += cleanup['bytes_freed']

    # Add human-readable sizes
    for cat in by_category:
        by_category[cat]['human'] = format_size(by_category[cat]['bytes'])

    return {
        'total_cleanups': len(stats['cleanups']),
        'total_saved': stats['total_saved'],
        'total_saved_human': format_size(stats['total_saved']),
        'first_run': stats['first_run'],
        'last_cleanup': stats['cleanups'][-1]['timestamp'] if stats['cleanups'] else None,
        'by_category': by_category,
        'recent': stats['cleanups'][-5:],  # Last 5 cleanups
    }


def print_stats():
    """Print statistics summary."""
    from .utils import print_header, Colors

    print_header("SPACE HOG STATISTICS")

    summary = get_summary()
    c = Colors

    if summary['total_cleanups'] == 0:
        print("  No cleanups recorded yet.")
        print("  Run cleanup commands and they'll be tracked here.")
        return

    print(f"  {c.BOLD}LIFETIME SAVINGS{c.RESET}")
    print(f"  {'-'*50}")
    print(f"  Total saved:    {c.GREEN}{summary['total_saved_human']}{c.RESET}")
    print(f"  Total cleanups: {summary['total_cleanups']}")
    print(f"  First cleanup:  {summary['first_run'][:10] if summary['first_run'] else 'N/A'}")
    print(f"  Last cleanup:   {summary['last_cleanup'][:10] if summary['last_cleanup'] else 'N/A'}")
    print()

    if summary['by_category']:
        print(f"  {c.BOLD}BY CATEGORY{c.RESET}")
        print(f"  {'-'*50}")
        for cat, data in sorted(summary['by_category'].items(), key=lambda x: -x[1]['bytes']):
            print(f"  {cat:<20} {data['human']:>10}  ({data['count']} cleanups)")
        print()

    if summary['recent']:
        print(f"  {c.BOLD}RECENT CLEANUPS{c.RESET}")
        print(f"  {'-'*50}")
        for cleanup in reversed(summary['recent']):
            date = cleanup['timestamp'][:10]
            size = format_size(cleanup['bytes_freed'])
            desc = cleanup['description'][:40]
            print(f"  {date}  {size:>10}  {desc}")
        print()

    # Current disk status
    disk = get_disk_usage()
    print(f"  {c.BOLD}CURRENT DISK{c.RESET}")
    print(f"  {'-'*50}")
    print(f"  Free:  {format_size(disk['free'])}")
    print(f"  Used:  {format_size(disk['used'])}")
    print(f"  Total: {format_size(disk['total'])}")
    print()
