"""User preferences for Space Hog.

Stores learned preferences about what apps/items are essential vs removable.
AI agents should use this to avoid repeatedly suggesting removal of essential items.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import format_size


PREFS_FILE = Path.home() / '.space-hog-preferences.json'


def load_preferences() -> dict:
    """Load user preferences from file."""
    if PREFS_FILE.exists():
        try:
            return json.loads(PREFS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {
        'essential_apps': [],      # Apps to never suggest removing
        'essential_paths': [],     # Paths to never suggest cleaning
        'blacklist_apps': [],      # Apps to always suggest removing
        'blacklist_paths': [],     # Paths to always suggest cleaning
        'decisions': [],           # History of user decisions for learning
        'notes': {},               # User notes about specific items
        'created': datetime.now().isoformat(),
        'updated': None,
    }


def save_preferences(prefs: dict):
    """Save preferences to file."""
    prefs['updated'] = datetime.now().isoformat()
    PREFS_FILE.write_text(json.dumps(prefs, indent=2))


def add_essential_app(app_name: str, reason: Optional[str] = None):
    """Mark an app as essential (never suggest removing)."""
    prefs = load_preferences()

    # Remove from blacklist if present
    prefs['blacklist_apps'] = [a for a in prefs['blacklist_apps'] if a.lower() != app_name.lower()]

    # Add to essential if not already there
    if not any(a.lower() == app_name.lower() for a in prefs['essential_apps']):
        prefs['essential_apps'].append(app_name)

    if reason:
        prefs['notes'][f'app:{app_name}'] = reason

    save_preferences(prefs)
    return prefs


def add_blacklist_app(app_name: str, reason: Optional[str] = None):
    """Mark an app as removable (always suggest removing)."""
    prefs = load_preferences()

    # Remove from essential if present
    prefs['essential_apps'] = [a for a in prefs['essential_apps'] if a.lower() != app_name.lower()]

    # Add to blacklist if not already there
    if not any(a.lower() == app_name.lower() for a in prefs['blacklist_apps']):
        prefs['blacklist_apps'].append(app_name)

    if reason:
        prefs['notes'][f'app:{app_name}'] = reason

    save_preferences(prefs)
    return prefs


def add_essential_path(path: str, reason: Optional[str] = None):
    """Mark a path as essential (never suggest cleaning)."""
    prefs = load_preferences()

    # Normalize path
    path = str(Path(path).expanduser())

    # Remove from blacklist if present
    prefs['blacklist_paths'] = [p for p in prefs['blacklist_paths'] if p != path]

    # Add to essential if not already there
    if path not in prefs['essential_paths']:
        prefs['essential_paths'].append(path)

    if reason:
        prefs['notes'][f'path:{path}'] = reason

    save_preferences(prefs)
    return prefs


def add_blacklist_path(path: str, reason: Optional[str] = None):
    """Mark a path as always cleanable."""
    prefs = load_preferences()

    # Normalize path
    path = str(Path(path).expanduser())

    # Remove from essential if present
    prefs['essential_paths'] = [p for p in prefs['essential_paths'] if p != path]

    # Add to blacklist if not already there
    if path not in prefs['blacklist_paths']:
        prefs['blacklist_paths'].append(path)

    if reason:
        prefs['notes'][f'path:{path}'] = reason

    save_preferences(prefs)
    return prefs


def record_decision(item_type: str, item_name: str, action: str, size_bytes: int = 0):
    """Record a user decision for learning.

    Args:
        item_type: 'app', 'cache', 'file', etc.
        item_name: Name of the item
        action: 'kept', 'removed', 'skipped'
        size_bytes: Size of the item
    """
    prefs = load_preferences()

    decision = {
        'timestamp': datetime.now().isoformat(),
        'type': item_type,
        'name': item_name,
        'action': action,
        'size_bytes': size_bytes,
    }

    prefs['decisions'].append(decision)

    # Keep last 100 decisions
    prefs['decisions'] = prefs['decisions'][-100:]

    save_preferences(prefs)
    return decision


def is_essential(item_name: str, item_path: Optional[str] = None) -> bool:
    """Check if an item is marked as essential."""
    prefs = load_preferences()

    # Check app name
    if any(a.lower() == item_name.lower() for a in prefs['essential_apps']):
        return True

    # Check path
    if item_path:
        path = str(Path(item_path).expanduser())
        if path in prefs['essential_paths']:
            return True
        # Check if path is under an essential path
        for essential in prefs['essential_paths']:
            if path.startswith(essential):
                return True

    return False


def is_blacklisted(item_name: str, item_path: Optional[str] = None) -> bool:
    """Check if an item is marked for removal."""
    prefs = load_preferences()

    # Check app name
    if any(a.lower() == item_name.lower() for a in prefs['blacklist_apps']):
        return True

    # Check path
    if item_path:
        path = str(Path(item_path).expanduser())
        if path in prefs['blacklist_paths']:
            return True

    return False


def get_note(item_name: str, item_path: Optional[str] = None) -> Optional[str]:
    """Get user note about an item."""
    prefs = load_preferences()

    # Check app note
    note = prefs['notes'].get(f'app:{item_name}')
    if note:
        return note

    # Check path note
    if item_path:
        path = str(Path(item_path).expanduser())
        note = prefs['notes'].get(f'path:{path}')
        if note:
            return note

    return None


def print_preferences():
    """Print current preferences."""
    from .utils import print_header, Colors

    print_header("USER PREFERENCES")
    prefs = load_preferences()
    c = Colors

    if prefs['essential_apps']:
        print(f"  {c.GREEN}{c.BOLD}ESSENTIAL APPS (never remove){c.RESET}")
        print(f"  {'-'*50}")
        for app in prefs['essential_apps']:
            note = prefs['notes'].get(f'app:{app}', '')
            note_str = f" - {note}" if note else ""
            print(f"    {app}{note_str}")
        print()

    if prefs['blacklist_apps']:
        print(f"  {c.RED}{c.BOLD}BLACKLIST APPS (always suggest removing){c.RESET}")
        print(f"  {'-'*50}")
        for app in prefs['blacklist_apps']:
            print(f"    {app}")
        print()

    if prefs['essential_paths']:
        print(f"  {c.GREEN}{c.BOLD}ESSENTIAL PATHS (never clean){c.RESET}")
        print(f"  {'-'*50}")
        for path in prefs['essential_paths']:
            print(f"    {path}")
        print()

    if not any([prefs['essential_apps'], prefs['blacklist_apps'], prefs['essential_paths']]):
        print("  No preferences set yet.")
        print()
        print("  AI agents will learn your preferences as you make decisions.")
        print("  You can also manually add preferences with:")
        print("    space-hog --essential 'App Name'")
        print("    space-hog --blacklist 'App Name'")
        print()

    # Recent decisions
    if prefs['decisions']:
        print(f"  {c.BOLD}RECENT DECISIONS{c.RESET}")
        print(f"  {'-'*50}")
        for decision in prefs['decisions'][-5:]:
            action_color = c.GREEN if decision['action'] == 'kept' else c.RED
            print(f"    {decision['name']}: {action_color}{decision['action']}{c.RESET}")
        print()
