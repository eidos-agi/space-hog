"""Cleanup advisor for Space Hog."""

import json
import subprocess
from pathlib import Path

from .utils import format_size, get_dir_size, print_header, Colors
from .constants import CACHE_LOCATIONS, CACHE_TO_CLEANUP, CLEANUP_INFO
from .caches import get_trash_size


def _has_unavailable_simulators() -> bool:
    """Check if there are any unavailable iOS simulators."""
    try:
        result = subprocess.run(
            ['xcrun', 'simctl', 'list', 'devices', 'unavailable'],
            capture_output=True, text=True, timeout=10
        )
        # If there are unavailable devices, output will have device lines
        # (not just headers like "== Devices ==" and "-- iOS X.X --")
        lines = result.stdout.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('==') and not line.startswith('--'):
                return True
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def collect_cleanup_opportunities() -> list[dict]:
    """Collect all cleanup opportunities with sizes and safety info."""
    opportunities = []

    # Check trash
    trash_size = get_trash_size()
    if trash_size > 0:
        info = CLEANUP_INFO['trash'].copy()
        info['size'] = trash_size
        info['size_human'] = format_size(trash_size)
        info['path'] = str(Path.home() / '.Trash')
        info['category'] = 'trash'
        opportunities.append(info)

    # Check all cache locations
    for location, description in CACHE_LOCATIONS:
        path = Path(location).expanduser()
        if path.exists():
            try:
                size = get_dir_size(path)
                if size > 50 * 1024 * 1024:  # Only include if > 50MB
                    # Find matching cleanup info
                    cleanup_key = None
                    for pattern, key in CACHE_TO_CLEANUP.items():
                        if location == pattern or location.startswith(pattern):
                            cleanup_key = key
                            break

                    if cleanup_key and cleanup_key in CLEANUP_INFO:
                        # Special case: only show simulators if there are unavailable ones
                        if cleanup_key == 'simulators' and not _has_unavailable_simulators():
                            continue

                        info = CLEANUP_INFO[cleanup_key].copy()
                        info['size'] = size
                        info['size_human'] = format_size(size)
                        info['path'] = str(path)
                        info['category'] = description
                        # Avoid duplicates
                        if not any(o.get('name') == info['name'] for o in opportunities):
                            opportunities.append(info)
                    else:
                        # Generic cache entry
                        opportunities.append({
                            'name': description,
                            'size': size,
                            'size_human': format_size(size),
                            'path': str(path),
                            'category': description,
                            'risk': 'UNKNOWN',
                            'risk_score': 3,
                            'command': f'rm -rf "{path}"/*',
                            'description': f'Cache directory: {description}',
                            'side_effects': ['May need to re-login or rebuild caches'],
                            'recommendation': 'Review contents before deleting.',
                        })
            except (PermissionError, OSError):
                pass

    return opportunities


def print_advise():
    """Print AI-friendly prioritized cleanup advice."""
    print_header("SPACE HOG ADVISOR")
    print()
    print(f"  {Colors.YELLOW}{Colors.BOLD}⚠️  WARNING: Review all commands before running.{Colors.RESET}")
    print(f"  {Colors.YELLOW}Space Hog is not responsible for data loss.{Colors.RESET}")
    print(f"  {Colors.YELLOW}Consider using --dry-run first to preview changes.{Colors.RESET}")
    print()
    print("  Scanning system for cleanup opportunities...\n")

    opportunities = collect_cleanup_opportunities()

    if not opportunities:
        print("  No significant cleanup opportunities found.")
        return

    # Sort by priority: SAFE first, then by size
    opportunities.sort(key=lambda x: (x.get('risk_score', 3), -x.get('size', 0)))

    # Calculate totals
    total_size = sum(o['size'] for o in opportunities)
    safe_size = sum(o['size'] for o in opportunities if o.get('risk') == 'SAFE')

    print(f"  Total reclaimable: {format_size(total_size)}")
    print(f"  Safe to reclaim:   {format_size(safe_size)}")
    print()

    # Group by risk level
    safe_ops = [o for o in opportunities if o.get('risk') == 'SAFE']
    moderate_ops = [o for o in opportunities if o.get('risk') == 'MODERATE']
    other_ops = [o for o in opportunities if o.get('risk') not in ('SAFE', 'MODERATE')]

    c = Colors

    if safe_ops:
        print(f"  {c.GREEN}{c.BOLD}PRIORITY 1: SAFE (no downside){c.RESET}")
        print(f"  {'-'*54}")
        for i, op in enumerate(safe_ops, 1):
            print(f"  {i}. {op['name']} - {c.BOLD}{op['size_human']}{c.RESET}")
            print(f"     {op['description']}")
            print(f"     Command: {op['command']}")
            print()

    if moderate_ops:
        print(f"  {c.YELLOW}{c.BOLD}PRIORITY 2: MODERATE (minor rebuild time){c.RESET}")
        print(f"  {'-'*54}")
        for i, op in enumerate(moderate_ops, len(safe_ops) + 1):
            print(f"  {i}. {op['name']} - {c.BOLD}{op['size_human']}{c.RESET}")
            print(f"     {op['description']}")
            print(f"     Side effects: {', '.join(op.get('side_effects', []))}")
            print(f"     Command: {op['command']}")
            print()

    if other_ops:
        print(f"  {c.RED}{c.BOLD}PRIORITY 3: REVIEW FIRST{c.RESET}")
        print(f"  {'-'*54}")
        for i, op in enumerate(other_ops, len(safe_ops) + len(moderate_ops) + 1):
            print(f"  {i}. {op['name']} - {c.BOLD}{op['size_human']}{c.RESET}")
            print(f"     Path: {op['path']}")
            print()

    # Quick command summary
    print_header("QUICK ACTIONS")

    if safe_ops:
        print(f"  {c.GREEN}Run all SAFE cleanups (reclaim {format_size(safe_size)}):{c.RESET}")
        print()
        for op in safe_ops:
            print(f"  {op['command']}")
        print()

    # Structured data for AI
    print_header("STRUCTURED DATA (for AI processing)")
    summary = {
        'total_reclaimable_bytes': total_size,
        'total_reclaimable_human': format_size(total_size),
        'safe_reclaimable_bytes': safe_size,
        'safe_reclaimable_human': format_size(safe_size),
        'opportunities': [
            {
                'name': o['name'],
                'size_bytes': o['size'],
                'size_human': o['size_human'],
                'risk': o.get('risk', 'UNKNOWN'),
                'command': o['command'],
                'side_effects': o.get('side_effects', []),
            }
            for o in opportunities
        ]
    }
    print(json.dumps(summary, indent=2))


def print_cleanup_guide():
    """Print detailed cleanup guide with safety information."""
    print_header("CLEANUP GUIDE")
    print("  Each command includes risk level and side effects.\n")

    # Use CLEANUP_INFO values
    for key, cmd in CLEANUP_INFO.items():
        risk_color = {
            'SAFE': Colors.GREEN,
            'MODERATE': Colors.YELLOW,
            'CAUTION': Colors.RED,
        }.get(cmd['risk'], '')

        print(f"  {'-'*56}")
        print(f"  {cmd['name']}")
        print(f"  Risk: {risk_color}{cmd['risk']}{Colors.RESET}")
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
