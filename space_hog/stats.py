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


# =============================================================================
# REGROWTH TRACKING
# =============================================================================

def calculate_regrowth() -> dict:
    """Calculate disk space regrowth since last cleanup.

    Returns dict with regrowth rate and time since last cleanup.
    """
    stats = load_stats()
    disk = get_disk_usage()

    if not stats['cleanups']:
        return {
            'has_data': False,
            'message': 'No cleanup history yet. Run some cleanups to track regrowth.',
        }

    last_cleanup = stats['cleanups'][-1]
    last_timestamp = datetime.fromisoformat(last_cleanup['timestamp'])
    now = datetime.now()
    days_since = (now - last_timestamp).days

    if days_since < 1:
        days_since = 1  # Avoid division by zero

    # Calculate space consumed since last cleanup
    disk_free_at_cleanup = last_cleanup.get('disk_free_after', disk['free'])
    space_consumed = disk_free_at_cleanup - disk['free']

    # Calculate rates
    rate_daily = space_consumed / days_since if days_since > 0 else 0
    rate_weekly = rate_daily * 7
    rate_monthly = rate_daily * 30

    return {
        'has_data': True,
        'days_since_cleanup': days_since,
        'last_cleanup_date': last_timestamp.strftime('%Y-%m-%d'),
        'disk_free_at_cleanup': disk_free_at_cleanup,
        'disk_free_at_cleanup_human': format_size(disk_free_at_cleanup),
        'disk_free_now': disk['free'],
        'disk_free_now_human': format_size(disk['free']),
        'space_consumed': max(0, space_consumed),
        'space_consumed_human': format_size(max(0, space_consumed)),
        'rate_daily': max(0, rate_daily),
        'rate_daily_human': format_size(max(0, rate_daily)),
        'rate_weekly': max(0, rate_weekly),
        'rate_weekly_human': format_size(max(0, rate_weekly)),
        'rate_monthly': max(0, rate_monthly),
        'rate_monthly_human': format_size(max(0, rate_monthly)),
    }


def identify_fastest_growing() -> list[dict]:
    """Identify categories with highest cleanup frequency.

    Uses cleanup history to identify which categories accumulate fastest.
    """
    stats = load_stats()

    if len(stats['cleanups']) < 2:
        return []

    # Group cleanups by category and calculate average cleanup frequency
    by_category: dict = {}
    for cleanup in stats['cleanups']:
        cat = cleanup.get('category', 'manual')
        if cat not in by_category:
            by_category[cat] = {
                'category': cat,
                'cleanups': [],
                'total_bytes': 0,
            }
        by_category[cat]['cleanups'].append(cleanup)
        by_category[cat]['total_bytes'] += cleanup['bytes_freed']

    # Calculate frequency and average size
    results = []
    for cat, data in by_category.items():
        count = len(data['cleanups'])
        if count >= 1:
            avg_size = data['total_bytes'] / count
            results.append({
                'category': cat,
                'cleanup_count': count,
                'total_bytes': data['total_bytes'],
                'total_human': format_size(data['total_bytes']),
                'avg_bytes': avg_size,
                'avg_human': format_size(avg_size),
            })

    # Sort by total bytes cleaned (most = fastest growing)
    results.sort(key=lambda x: -x['total_bytes'])
    return results[:5]  # Top 5


def suggest_cleanup_frequency() -> dict:
    """Suggest optimal cleanup frequency based on regrowth.

    Returns recommended interval and next cleanup date.
    """
    regrowth = calculate_regrowth()

    if not regrowth.get('has_data'):
        return {
            'has_recommendation': False,
            'message': 'Need more cleanup history for recommendations.',
        }

    # Calculate when disk would reach 90% full at current rate
    disk = get_disk_usage()
    free_percentage = disk['free'] / disk['total']

    rate_daily = regrowth.get('rate_daily', 0)
    if rate_daily <= 0:
        return {
            'has_recommendation': True,
            'recommended_interval_days': 30,
            'reason': 'Low disk activity detected',
            'next_cleanup_date': (datetime.now() + timedelta(days=30)).strftime('%b %d'),
        }

    # Days until we'd hit 10% free space
    target_free = disk['total'] * 0.10
    space_buffer = disk['free'] - target_free
    days_until_critical = space_buffer / rate_daily if rate_daily > 0 else 365

    # Recommend cleaning at half that interval
    recommended = max(7, min(30, int(days_until_critical / 2)))

    return {
        'has_recommendation': True,
        'recommended_interval_days': recommended,
        'reason': f'Based on {regrowth["rate_weekly_human"]}/week regrowth',
        'next_cleanup_date': (datetime.now() + timedelta(days=recommended)).strftime('%b %d'),
        'days_until_critical': int(days_until_critical),
    }


def print_regrowth_report():
    """Print regrowth tracking report."""
    from .utils import print_header, Colors

    print_header("REGROWTH TRACKING")
    c = Colors

    regrowth = calculate_regrowth()

    if not regrowth.get('has_data'):
        print(f"  {regrowth['message']}")
        print()
        return

    print(f"  {c.BOLD}SINCE LAST CLEANUP{c.RESET}")
    print(f"  {'-'*50}")
    print(f"  Last cleanup:    {regrowth['last_cleanup_date']} ({regrowth['days_since_cleanup']} days ago)")
    print(f"  Free at cleanup: {regrowth['disk_free_at_cleanup_human']}")
    print(f"  Free now:        {regrowth['disk_free_now_human']}")
    print(f"  Space consumed:  {c.YELLOW}{regrowth['space_consumed_human']}{c.RESET}")
    print()

    print(f"  {c.BOLD}REGROWTH RATE{c.RESET}")
    print(f"  {'-'*50}")
    print(f"  Daily:   {regrowth['rate_daily_human']}/day")
    print(f"  Weekly:  {regrowth['rate_weekly_human']}/week")
    print(f"  Monthly: {regrowth['rate_monthly_human']}/month (projected)")
    print()

    # Fastest growing categories
    fastest = identify_fastest_growing()
    if fastest:
        print(f"  {c.BOLD}MOST CLEANED CATEGORIES{c.RESET}")
        print(f"  {'-'*50}")
        for item in fastest:
            print(f"  {item['category']:<20} {item['total_human']:>10}  ({item['cleanup_count']} cleanups)")
        print()

    # Recommendation
    suggestion = suggest_cleanup_frequency()
    if suggestion.get('has_recommendation'):
        print(f"  {c.BOLD}RECOMMENDATION{c.RESET}")
        print(f"  {'-'*50}")
        print(f"  Clean every {suggestion['recommended_interval_days']} days")
        print(f"  Next suggested cleanup: {c.GREEN}{suggestion['next_cleanup_date']}{c.RESET}")
        print(f"  Reason: {suggestion['reason']}")
        print()


# =============================================================================
# CLEANUP SESSION MANAGEMENT
# =============================================================================

def start_cleanup_session() -> dict:
    """Start a cleanup session, recording initial state.

    Returns session dict to track cleanup progress.
    """
    disk = get_disk_usage()
    return {
        'session_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'started_at': datetime.now().isoformat(),
        'disk_free_before': disk['free'],
        'disk_free_before_human': format_size(disk['free']),
        'cleanups': [],
    }


def end_cleanup_session(session: dict) -> dict:
    """End a cleanup session, calculating totals.

    Returns completed session with summary.
    """
    disk = get_disk_usage()
    total_freed = disk['free'] - session['disk_free_before']

    session['ended_at'] = datetime.now().isoformat()
    session['disk_free_after'] = disk['free']
    session['disk_free_after_human'] = format_size(disk['free'])
    session['total_freed'] = max(0, total_freed)
    session['total_freed_human'] = format_size(max(0, total_freed))
    session['cleanup_count'] = len(session['cleanups'])

    # Add prediction for next cleanup
    suggestion = suggest_cleanup_frequency()
    if suggestion.get('has_recommendation'):
        session['next_cleanup_date'] = suggestion['next_cleanup_date']
        session['recommended_interval_days'] = suggestion['recommended_interval_days']

    return session


def print_post_cleanup_summary(session: dict):
    """Print post-cleanup summary."""
    from .utils import print_header, Colors

    print_header("CLEANUP COMPLETE")
    c = Colors

    print(f"  Before:  {session['disk_free_before_human']} free")
    print(f"  After:   {c.GREEN}{session['disk_free_after_human']}{c.RESET} free")
    print(f"  {'─'*30}")
    print(f"  Freed:   {c.GREEN}{c.BOLD}{session['total_freed_human']}{c.RESET}")
    print()

    if session['cleanups']:
        print(f"  {c.BOLD}THIS SESSION{c.RESET}")
        print(f"  {'-'*50}")
        for cleanup in session['cleanups']:
            print(f"    - {cleanup['description']} ({cleanup.get('freed_human', 'N/A')})")
        print()

    # Cumulative savings
    summary = get_summary()
    if summary['total_saved'] > 0:
        print(f"  {c.BOLD}CUMULATIVE SAVINGS (all time){c.RESET}: {c.GREEN}{summary['total_saved_human']}{c.RESET}")
        print()

    # Next cleanup suggestion
    if session.get('next_cleanup_date'):
        print(f"  Based on your regrowth rate, next cleanup in ~{session.get('recommended_interval_days', 14)} days ({session['next_cleanup_date']})")
        print()


# Need to import timedelta for regrowth calculations
from datetime import timedelta
