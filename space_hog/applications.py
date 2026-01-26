"""Application analysis for Space Hog.

Finds installed applications, their sizes, last used dates, and suggests
apps that may no longer be needed (especially those AI can replace).
"""

import subprocess
import plistlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import format_size, get_dir_size, Colors


# Apps that AI assistants can often replace or reduce need for
AI_REPLACEABLE_APPS = {
    # Writing/Docs
    'Grammarly': 'AI can check grammar and improve writing',
    'Hemingway Editor': 'AI can simplify and improve writing style',
    'ProWritingAid': 'AI provides writing feedback and suggestions',

    # Translation
    'Google Translate': 'AI can translate text in context',
    'DeepL': 'AI handles translation natively',

    # Note-taking (if only used for quick capture)
    'Evernote': 'AI can help organize and retrieve information',
    'OneNote': 'AI can help organize and retrieve information',

    # Simple image editing
    'Preview': 'Keep - system app',  # Exception - keep
    'Pixelmator': 'AI can generate and edit images',

    # Code helpers
    'Dash': 'AI has documentation knowledge built-in',
    'SourceTree': 'AI can help with git commands',

    # Research
    'DEVONthink': 'AI can help research and synthesize information',
    'Pocket': 'AI can summarize articles on demand',
    'Instapaper': 'AI can summarize articles on demand',

    # Calculators/Converters
    'Calculator': 'Keep - system app',  # Exception
    'Numi': 'AI handles calculations and conversions',
    'Soulver': 'AI handles calculations and conversions',

    # Email
    'Spark': 'AI can draft and summarize emails',
    'Airmail': 'AI can draft and summarize emails',
}

# System apps that should never be suggested for removal
SYSTEM_APPS = {
    'Finder', 'Safari', 'Mail', 'Calendar', 'Notes', 'Reminders',
    'Photos', 'FaceTime', 'Messages', 'Maps', 'News', 'Stocks',
    'Home', 'Voice Memos', 'Preview', 'Music', 'Podcasts', 'TV',
    'Books', 'App Store', 'System Preferences', 'System Settings',
    'Terminal', 'Activity Monitor', 'Disk Utility', 'Console',
    'Keychain Access', 'Calculator', 'Clock', 'Contacts',
}


def get_app_last_used(app_path: Path) -> Optional[datetime]:
    """Get the last used date for an application using Spotlight metadata."""
    try:
        result = subprocess.run(
            ['mdls', '-name', 'kMDItemLastUsedDate', '-raw', str(app_path)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip() != '(null)':
            # Parse date like "2024-01-15 10:30:00 +0000"
            date_str = result.stdout.strip()
            try:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z')
            except ValueError:
                pass
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


def get_app_info(app_path: Path) -> dict:
    """Get information about an application."""
    info = {
        'name': app_path.stem,
        'path': str(app_path),
        'size': 0,
        'size_human': '0 B',
        'last_used': None,
        'last_used_str': 'Unknown',
        'days_since_used': None,
        'ai_replaceable': False,
        'ai_reason': None,
        'is_system': False,
        'version': None,
    }

    # Get size
    info['size'] = get_dir_size(app_path)
    info['size_human'] = format_size(info['size'])

    # Get last used
    last_used = get_app_last_used(app_path)
    if last_used:
        info['last_used'] = last_used.isoformat()
        info['last_used_str'] = last_used.strftime('%Y-%m-%d')
        info['days_since_used'] = (datetime.now(last_used.tzinfo) - last_used).days

    # Check if AI replaceable
    app_name = app_path.stem
    if app_name in AI_REPLACEABLE_APPS:
        reason = AI_REPLACEABLE_APPS[app_name]
        if not reason.startswith('Keep'):
            info['ai_replaceable'] = True
            info['ai_reason'] = reason

    # Check if system app
    info['is_system'] = app_name in SYSTEM_APPS

    # Try to get version from Info.plist
    info_plist = app_path / 'Contents' / 'Info.plist'
    if info_plist.exists():
        try:
            with open(info_plist, 'rb') as f:
                plist = plistlib.load(f)
                info['version'] = plist.get('CFBundleShortVersionString',
                                           plist.get('CFBundleVersion'))
        except Exception:
            pass

    return info


def scan_applications(min_size_mb: int = 50, min_days_unused: int = 90) -> dict:
    """Scan /Applications for apps and categorize them."""
    results = {
        'all_apps': [],
        'unused_apps': [],  # Not used in min_days_unused
        'ai_replaceable': [],  # Could be replaced by AI
        'large_apps': [],  # Larger than min_size_mb
        'total_size': 0,
        'reclaimable_size': 0,  # Unused + AI replaceable
    }

    apps_dir = Path('/Applications')
    if not apps_dir.exists():
        return results

    for app_path in apps_dir.glob('*.app'):
        info = get_app_info(app_path)
        results['all_apps'].append(info)
        results['total_size'] += info['size']

        # Skip system apps for recommendations
        if info['is_system']:
            continue

        # Check if unused
        if info['days_since_used'] is not None and info['days_since_used'] > min_days_unused:
            results['unused_apps'].append(info)
            results['reclaimable_size'] += info['size']

        # Check if AI replaceable (and not already in unused)
        if info['ai_replaceable'] and info not in results['unused_apps']:
            results['ai_replaceable'].append(info)
            # Don't double count if already in unused

        # Check if large
        if info['size'] > min_size_mb * 1024 * 1024:
            results['large_apps'].append(info)

    # Sort by size
    results['all_apps'].sort(key=lambda x: -x['size'])
    results['unused_apps'].sort(key=lambda x: -x['size'])
    results['ai_replaceable'].sort(key=lambda x: -x['size'])
    results['large_apps'].sort(key=lambda x: -x['size'])

    return results


def print_applications_analysis(min_days_unused: int = 90):
    """Print applications analysis."""
    from .utils import print_header

    print_header("APPLICATIONS ANALYSIS")
    print(f"  Scanning /Applications...\n")

    results = scan_applications(min_days_unused=min_days_unused)
    c = Colors

    # Summary
    print(f"  {c.BOLD}SUMMARY{c.RESET}")
    print(f"  {'-'*50}")
    print(f"  Total applications: {len(results['all_apps'])}")
    print(f"  Total size: {format_size(results['total_size'])}")
    print(f"  Unused ({min_days_unused}+ days): {len(results['unused_apps'])} apps")
    print(f"  AI replaceable: {len(results['ai_replaceable'])} apps")
    print()

    # Unused apps
    if results['unused_apps']:
        from .preferences import is_essential, is_blacklisted
        print(f"  {c.YELLOW}{c.BOLD}UNUSED APPS (not opened in {min_days_unused}+ days){c.RESET}")
        print(f"  {'-'*50}")
        for app in results['unused_apps'][:10]:
            days = app['days_since_used']
            markers = []
            if is_essential(app['name']):
                markers.append(f"{c.GREEN}essential{c.RESET}")
            if is_blacklisted(app['name']):
                markers.append(f"{c.RED}blacklisted{c.RESET}")
            marker_str = f" ({', '.join(markers)})" if markers else ""
            print(f"  {app['size_human']:>10}  {app['name']}{marker_str}")
            print(f"             Last used: {app['last_used_str']} ({days} days ago)")
        if len(results['unused_apps']) > 10:
            print(f"  ... and {len(results['unused_apps']) - 10} more unused apps")
        unused_size = sum(a['size'] for a in results['unused_apps'])
        print(f"\n  {c.YELLOW}Potential savings: {format_size(unused_size)}{c.RESET}")
        print()

    # AI replaceable
    if results['ai_replaceable']:
        print(f"  {c.GREEN}{c.BOLD}AI-REPLACEABLE APPS{c.RESET}")
        print(f"  {'-'*50}")
        print(f"  These apps do tasks that AI assistants can handle:\n")
        for app in results['ai_replaceable'][:10]:
            print(f"  {app['size_human']:>10}  {app['name']}")
            print(f"             {c.GREEN}→ {app['ai_reason']}{c.RESET}")
        print()

    # Large apps
    if results['large_apps']:
        print(f"  {c.BOLD}LARGEST APPS{c.RESET}")
        print(f"  {'-'*50}")
        for app in results['large_apps'][:10]:
            markers = []
            if app in results['unused_apps']:
                markers.append(f'{c.YELLOW}unused{c.RESET}')
            if app['ai_replaceable']:
                markers.append(f'{c.GREEN}AI-replaceable{c.RESET}')
            marker_str = f" ({', '.join(markers)})" if markers else ""
            print(f"  {app['size_human']:>10}  {app['name']}{marker_str}")
        print()

    # Cleanup command
    if results['unused_apps']:
        print(f"  {c.BOLD}TO REMOVE AN APP:{c.RESET}")
        print(f"  {'-'*50}")
        print(f"  # Move to trash (recoverable)")
        print(f"  mv '/Applications/AppName.app' ~/.Trash/")
        print()
        print(f"  # Or use AppCleaner to remove app + associated files")
        print(f"  # https://freemacsoft.net/appcleaner/")
        print()
