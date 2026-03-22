"""Read shared Eidos Mac user profile.

Profile is created by apple-a-day (`aad profile`) and stored at
~/.config/eidos/mac-profile.json. space-hog reads it to tailor
recommendations to the user type.

If no profile exists, space-hog can generate a minimal one itself.
"""

import json
from pathlib import Path


PROFILE_PATH = Path.home() / ".config" / "eidos" / "mac-profile.json"


def load_profile() -> dict | None:
    """Load the shared Eidos Mac profile. Returns None if not found."""
    if PROFILE_PATH.exists():
        try:
            return json.loads(PROFILE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def get_user_type() -> str:
    """Get user type string, or 'unknown' if no profile."""
    profile = load_profile()
    if profile:
        return profile.get("user_type", "unknown")
    return "unknown"


def get_tags() -> set[str]:
    """Get user tags as a set."""
    profile = load_profile()
    if profile:
        return set(profile.get("tags", []))
    return set()


def has_tag(tag: str) -> bool:
    """Check if user has a specific tag."""
    return tag in get_tags()
