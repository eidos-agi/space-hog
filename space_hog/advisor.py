"""Cleanup advisor for Space Hog."""

import json
import shutil
import subprocess
from pathlib import Path

from .utils import format_size, get_dir_size, print_header, Colors
from .constants import (
    CACHE_LOCATIONS, CACHE_TO_CLEANUP, CLEANUP_INFO,
    TYPICAL_BASELINES, ANOMALY_THRESHOLD, PERSONA_INDICATORS,
    CLEANUP_TIERS, DISK_STATUS,
)
from .caches import get_trash_size
from .preferences import is_essential, is_blacklisted, get_note


# =============================================================================
# DISK HEALTH ASSESSMENT
# =============================================================================

def get_disk_health() -> dict:
    """Get comprehensive disk health assessment.

    Returns dict with disk stats, status, and quick wins.
    """
    total, used, free = shutil.disk_usage("/")
    percentage_free = free / total
    percentage_used = used / total

    # Determine status
    if percentage_free < DISK_STATUS['CRITICAL']['threshold']:
        status = 'CRITICAL'
    elif percentage_free < DISK_STATUS['LOW']['threshold']:
        status = 'LOW'
    else:
        status = 'HEALTHY'

    status_info = DISK_STATUS[status]

    return {
        'total': total,
        'used': used,
        'free': free,
        'total_human': format_size(total),
        'used_human': format_size(used),
        'free_human': format_size(free),
        'percentage_free': percentage_free * 100,
        'percentage_used': percentage_used * 100,
        'status': status,
        'status_message': status_info['message'],
        'status_color': status_info['color'],
    }


def get_quick_wins(opportunities: list[dict]) -> dict:
    """Calculate instant-reclaim opportunities (Trash + safe caches).

    Returns dict with quick win summary.
    """
    trash_size = get_trash_size()
    safe_items = [o for o in opportunities if o.get('risk') == 'SAFE']
    safe_size = sum(o['size'] for o in safe_items)

    return {
        'trash_size': trash_size,
        'trash_size_human': format_size(trash_size),
        'safe_cache_size': safe_size - trash_size,  # Exclude trash to avoid double-count
        'safe_cache_size_human': format_size(max(0, safe_size - trash_size)),
        'instant_reclaim': safe_size,
        'instant_reclaim_human': format_size(safe_size),
        'item_count': len(safe_items),
    }


def print_situation_assessment(disk_health: dict, quick_wins: dict):
    """Print the disk health header at the top of --advise output."""
    c = Colors
    status_color = getattr(c, disk_health['status_color'], '')

    print_header("DISK STATUS")
    print(f"  Total: {disk_health['total_human']} | "
          f"Used: {disk_health['used_human']} ({disk_health['percentage_used']:.0f}%) | "
          f"Free: {disk_health['free_human']}")
    print()
    print(f"  Status: {status_color}{disk_health['status_message']}{c.RESET}")
    print()

    if quick_wins['instant_reclaim'] > 0:
        print(f"  {c.BOLD}Quick Wins (safe, instant):{c.RESET}")
        if quick_wins['trash_size'] > 0:
            print(f"    Trash:        {quick_wins['trash_size_human']}")
        if quick_wins['safe_cache_size'] > 0:
            print(f"    Safe caches:  {quick_wins['safe_cache_size_human']}")
        print(f"    {'─'*20}")
        print(f"    Total:        {c.GREEN}{quick_wins['instant_reclaim_human']}{c.RESET}")
        print()


# =============================================================================
# PERSONA DETECTION
# =============================================================================

def detect_personas() -> list[dict]:
    """Detect user personas based on installed tools and cache sizes.

    Returns list of detected personas, sorted by match strength.
    """
    detected = []

    for key, persona in PERSONA_INDICATORS.items():
        matches = []
        total_size = 0

        # Check paths
        for path_pattern, min_size in persona['paths']:
            path = Path(path_pattern).expanduser()
            if path.exists():
                try:
                    size = get_dir_size(path)
                    if size >= min_size:
                        matches.append({'path': str(path), 'size': size})
                        total_size += size
                except (PermissionError, OSError):
                    pass

        # Check commands
        for cmd in persona.get('commands', []):
            try:
                result = subprocess.run(
                    ['which', cmd], capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    matches.append({'command': cmd, 'available': True})
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        if matches:
            detected.append({
                'key': key,
                'name': persona['name'],
                'emoji': persona.get('emoji', ''),
                'match_count': len(matches),
                'total_size': total_size,
                'total_size_human': format_size(total_size),
                'priority_categories': persona.get('priority_categories', []),
            })

    # Sort by total size (heaviest footprint first)
    detected.sort(key=lambda x: -x['total_size'])
    return detected


def print_persona_header(personas: list[dict]):
    """Print detected personas at the top of output."""
    if not personas:
        return

    c = Colors
    names = [f"{p['emoji']} {p['name']}" for p in personas[:4]]  # Top 4
    print_header("DETECTED PROFILE")
    print(f"  {', '.join(names)}")
    print()


# =============================================================================
# ANOMALY CLASSIFICATION
# =============================================================================

def classify_anomalies(opportunities: list[dict]) -> dict:
    """Classify cleanup opportunities as normal or anomalous.

    Returns dict with anomalies, normal items, and unknown items.
    """
    anomalies = []
    normal = []
    unknown = []

    for op in opportunities:
        # Try to find matching baseline
        category = None
        for path_pattern, cat_key in CACHE_TO_CLEANUP.items():
            if op.get('path', '').startswith(str(Path(path_pattern).expanduser())):
                category = cat_key
                break

        # Also check by cleanup info key
        if not category:
            for key in CLEANUP_INFO:
                if CLEANUP_INFO[key].get('name') == op.get('name'):
                    category = key
                    break

        if category and category in TYPICAL_BASELINES:
            baseline = TYPICAL_BASELINES[category]
            deviation = op['size'] / baseline if baseline > 0 else 0
            op['baseline'] = baseline
            op['baseline_human'] = format_size(baseline)
            op['deviation'] = deviation
            op['category_key'] = category

            if deviation > ANOMALY_THRESHOLD:
                op['is_anomaly'] = True
                anomalies.append(op)
            else:
                op['is_anomaly'] = False
                normal.append(op)
        else:
            op['is_anomaly'] = None
            unknown.append(op)

    # Sort anomalies by deviation (most anomalous first)
    anomalies.sort(key=lambda x: -x.get('deviation', 0))

    return {
        'anomalies': anomalies,
        'normal': normal,
        'unknown': unknown,
    }


def print_anomaly_report(classified: dict):
    """Print anomaly-focused report."""
    c = Colors
    anomalies = classified['anomalies']
    normal = classified['normal']

    if anomalies:
        print_header("ANOMALIES DETECTED")
        for op in anomalies:
            deviation = op.get('deviation', 0)
            print(f"  {c.YELLOW}[!]{c.RESET} {op['name']}: {c.BOLD}{op['size_human']}{c.RESET} "
                  f"({deviation:.1f}x typical)")
            print(f"      Expected: ~{op.get('baseline_human', 'unknown')}")
            if op.get('side_effects'):
                print(f"      Action: {op.get('command', 'N/A')}")
            print()

    if normal:
        print(f"  {c.BOLD}WITHIN NORMAL RANGE{c.RESET}")
        print(f"  {'-'*50}")
        for op in normal[:5]:  # Top 5 normal items
            print(f"  {c.GREEN}[OK]{c.RESET} {op['name']}: {op['size_human']} (typical)")
        if len(normal) > 5:
            print(f"  ... and {len(normal) - 5} more normal items")
        print()


# =============================================================================
# SMART ACTIONS (TIERED RECOMMENDATIONS)
# =============================================================================

def calculate_tier_savings(opportunities: list[dict]) -> dict:
    """Calculate potential savings for each cleanup tier.

    Returns dict with tier number -> savings info.
    """
    tier_results = {}

    for tier_num, tier_info in CLEANUP_TIERS.items():
        tier_items = []
        tier_categories = tier_info['categories']

        # Include items from previous tier if specified
        if tier_info.get('includes_tier'):
            prev_tier = tier_results.get(tier_info['includes_tier'])
            if prev_tier:
                tier_items = list(prev_tier['items'])

        # Add items matching this tier's categories
        for op in opportunities:
            # Match by category key
            category_key = op.get('category_key')
            if category_key and category_key in tier_categories:
                if op not in tier_items:
                    tier_items.append(op)
                continue

            # Also match by risk level
            if op.get('risk_score', 3) <= tier_info.get('risk_max', 1):
                # Check if category name matches
                for cat in tier_categories:
                    if cat in op.get('name', '').lower() or cat in op.get('path', '').lower():
                        if op not in tier_items:
                            tier_items.append(op)
                        break

        tier_size = sum(item['size'] for item in tier_items)

        tier_results[tier_num] = {
            'tier': tier_num,
            'name': tier_info['name'],
            'description': tier_info['description'],
            'items': tier_items,
            'size': tier_size,
            'size_human': format_size(tier_size),
            'item_count': len(tier_items),
            'interactive': tier_info.get('interactive', False),
        }

    return tier_results


def print_smart_actions(tier_savings: dict, opportunities: list[dict]):
    """Print actionable cleanup tiers."""
    c = Colors

    print_header("SMART CLEANUP OPTIONS")

    for tier_num in sorted(tier_savings.keys()):
        tier = tier_savings[tier_num]
        if tier['size'] == 0:
            continue

        # Calculate incremental vs cumulative
        if tier_num == 1:
            incremental = tier['size_human']
            cumulative = tier['size_human']
        else:
            prev_size = tier_savings.get(tier_num - 1, {}).get('size', 0)
            increment = tier['size'] - prev_size
            incremental = f"+{format_size(increment)}"
            cumulative = f"{tier['size_human']} total"

        interactive = " (interactive)" if tier.get('interactive') else ""

        print(f"  [{tier_num}] {tier['name']:<25} {incremental:>12}")
        print(f"      {tier['description']}{interactive}")
        if tier_num > 1:
            print(f"      Cumulative: {cumulative}")
        print()

    # Custom option
    total_size = sum(o['size'] for o in opportunities)
    print(f"  [4] Custom                       Select individual items")
    print(f"      Total available: {format_size(total_size)}")
    print()


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
        info['category_key'] = 'trash'  # For anomaly detection
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
                        info['category_key'] = cleanup_key  # For anomaly detection
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
                            'category_key': None,
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
    """Print AI-friendly prioritized cleanup advice with enhanced UX."""
    c = Colors

    # Collect all data first
    opportunities = collect_cleanup_opportunities()
    disk_health = get_disk_health()
    personas = detect_personas()

    # Sort by priority: SAFE first, then by size
    opportunities.sort(key=lambda x: (x.get('risk_score', 3), -x.get('size', 0)))

    # Calculate quick wins
    quick_wins = get_quick_wins(opportunities)

    # Classify anomalies
    classified = classify_anomalies(opportunities)

    # Calculate tier savings
    tier_savings = calculate_tier_savings(opportunities)

    # =========================================================================
    # SECTION 1: DISK STATUS
    # =========================================================================
    print_situation_assessment(disk_health, quick_wins)

    # =========================================================================
    # SECTION 2: DETECTED PROFILE
    # =========================================================================
    print_persona_header(personas)

    # =========================================================================
    # SECTION 3: ANOMALIES
    # =========================================================================
    if classified['anomalies']:
        print_anomaly_report(classified)

    # =========================================================================
    # SECTION 4: SMART CLEANUP OPTIONS
    # =========================================================================
    print_smart_actions(tier_savings, opportunities)

    # =========================================================================
    # SECTION 5: LARGEST APPS
    # =========================================================================
    from .applications import scan_applications
    app_results = scan_applications(min_days_unused=90)
    if app_results['large_apps']:
        print_header("LARGEST APPS")
        for app in app_results['large_apps'][:5]:
            markers = []
            if is_essential(app['name']):
                markers.append(f'{c.GREEN}essential{c.RESET}')
            elif is_blacklisted(app['name']):
                markers.append(f'{c.RED}remove{c.RESET}')
            elif app in app_results['unused_apps']:
                markers.append(f'{c.YELLOW}unused {app["days_since_used"]}d{c.RESET}')
            marker_str = f" ({', '.join(markers)})" if markers else ""
            print(f"  {app['size_human']:>10}  {app['name']}{marker_str}")

        # Filter unused apps - exclude essential, prioritize blacklisted
        removable_apps = [a for a in app_results['unused_apps'] if not is_essential(a['name'])]
        if removable_apps:
            unused_size = sum(a['size'] for a in removable_apps)
            print()
            print(f"  {c.YELLOW}Unused apps (90+ days): {format_size(unused_size)} reclaimable{c.RESET}")

        print(f"  Run: space-hog --apps for full details")
        print()

    # =========================================================================
    # SECTION 6: REGROWTH TRACKING (if history exists)
    # =========================================================================
    from .stats import calculate_regrowth, suggest_cleanup_frequency
    regrowth = calculate_regrowth()
    if regrowth.get('has_data') and regrowth.get('days_since_cleanup', 0) >= 1:
        print_header("REGROWTH TRACKING")
        print(f"  Last cleanup: {regrowth['last_cleanup_date']} ({regrowth['days_since_cleanup']} days ago)")
        print(f"  Regrowth rate: {regrowth['rate_weekly_human']}/week")

        suggestion = suggest_cleanup_frequency()
        if suggestion.get('has_recommendation'):
            print(f"  Recommendation: Clean every {suggestion['recommended_interval_days']} days")
        print()

    # =========================================================================
    # SECTION 7: DETAILED BREAKDOWN (collapsed)
    # =========================================================================
    total_size = sum(o['size'] for o in opportunities)
    safe_size = sum(o['size'] for o in opportunities if o.get('risk') == 'SAFE')

    safe_ops = [o for o in opportunities if o.get('risk') == 'SAFE']
    moderate_ops = [o for o in opportunities if o.get('risk') == 'MODERATE']
    other_ops = [o for o in opportunities if o.get('risk') not in ('SAFE', 'MODERATE')]

    print_header("DETAILED BREAKDOWN")
    print(f"  Total reclaimable: {format_size(total_size)}")
    print(f"  Safe to reclaim:   {format_size(safe_size)}")
    print()

    if safe_ops:
        print(f"  {c.GREEN}{c.BOLD}SAFE ({len(safe_ops)} items, {format_size(safe_size)}){c.RESET}")
        for op in safe_ops:
            print(f"    • {op['name']}: {op['size_human']}")
        print()

    if moderate_ops:
        mod_size = sum(o['size'] for o in moderate_ops)
        print(f"  {c.YELLOW}{c.BOLD}MODERATE ({len(moderate_ops)} items, {format_size(mod_size)}){c.RESET}")
        for op in moderate_ops:
            print(f"    • {op['name']}: {op['size_human']}")
        print()

    if other_ops:
        other_size = sum(o['size'] for o in other_ops)
        print(f"  {c.RED}{c.BOLD}REVIEW FIRST ({len(other_ops)} items, {format_size(other_size)}){c.RESET}")
        for op in other_ops[:5]:
            print(f"    • {op['name']}: {op['size_human']}")
        if len(other_ops) > 5:
            print(f"    ... and {len(other_ops) - 5} more")
        print()

    # =========================================================================
    # SECTION 8: STRUCTURED DATA (for AI processing)
    # =========================================================================
    print_header("STRUCTURED DATA (for AI processing)")
    summary = {
        'disk_health': {
            'total_bytes': disk_health['total'],
            'used_bytes': disk_health['used'],
            'free_bytes': disk_health['free'],
            'percentage_used': disk_health['percentage_used'],
            'status': disk_health['status'],
        },
        'quick_wins': {
            'trash_bytes': quick_wins['trash_size'],
            'safe_cache_bytes': quick_wins['safe_cache_size'],
            'instant_reclaim_bytes': quick_wins['instant_reclaim'],
            'instant_reclaim_human': quick_wins['instant_reclaim_human'],
        },
        'personas': [p['key'] for p in personas],
        'anomalies': [
            {
                'name': a['name'],
                'size_bytes': a['size'],
                'baseline_bytes': a.get('baseline', 0),
                'deviation': a.get('deviation', 0),
            }
            for a in classified['anomalies']
        ],
        'tiers': {
            str(num): {
                'name': t['name'],
                'size_bytes': t['size'],
                'size_human': t['size_human'],
                'item_count': t['item_count'],
            }
            for num, t in tier_savings.items()
        },
        'regrowth': {
            'days_since_cleanup': regrowth.get('days_since_cleanup'),
            'rate_daily_bytes': regrowth.get('rate_daily'),
            'rate_weekly_human': regrowth.get('rate_weekly_human'),
        } if regrowth.get('has_data') else None,
        'apps': {
            'total_count': len(app_results['all_apps']),
            'total_size': app_results['total_size'],
            'unused_count': len(app_results['unused_apps']),
            'unused_size': sum(a['size'] for a in app_results['unused_apps']),
            'largest': [
                {'name': a['name'], 'size': a['size'], 'days_unused': a.get('days_since_used')}
                for a in app_results['large_apps'][:5]
            ],
        },
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
                'category_key': o.get('category_key'),
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
