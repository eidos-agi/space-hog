"""CLI entry point for Space Hog."""

import sys
import argparse
from pathlib import Path

from .utils import format_size, print_header, Colors
from .caches import check_caches
from .scanners import find_large_files, find_space_hogs
from .docker import print_docker_analysis
from .advisor import print_advise, print_cleanup_guide
from .applications import print_applications_analysis
from .stats import print_stats, print_regrowth_report
from .runner import scan_all
from .smart import get_smart_recommendations
from .memory import print_memory_analysis
from .preferences import print_preferences, add_essential_app, add_blacklist_app
from .unused import print_unused_report


def print_full_report():
    """Print complete system health report."""
    import shutil
    from .advisor import get_disk_health, detect_personas, collect_cleanup_opportunities, classify_anomalies
    from .memory import get_top_ram_consumers, aggregate_by_app, get_login_items
    from .applications import scan_applications
    from .stats import get_summary, calculate_regrowth
    from .preferences import load_preferences, is_essential

    c = Colors

    # ==========================================================================
    # EXECUTIVE SUMMARY
    # ==========================================================================
    print_header("SYSTEM HEALTH SUMMARY")

    disk = get_disk_health()
    status_color = getattr(c, disk['status_color'], '')

    print(f"  {c.BOLD}DISK{c.RESET}")
    print(f"    Status:     {status_color}{disk['status']}{c.RESET}")
    print(f"    Free:       {disk['free_human']} / {disk['total_human']} ({100-disk['percentage_used']:.0f}%)")

    # RAM
    processes = get_top_ram_consumers(limit=20)
    aggregated = aggregate_by_app(processes)
    total_ram = sum(a['rss_bytes'] for a in aggregated[:10])
    print()
    print(f"  {c.BOLD}MEMORY{c.RESET}")
    print(f"    Top 10 apps: {format_size(total_ram)} RAM")
    if aggregated:
        top_app = aggregated[0]
        essential_marker = f" {c.GREEN}(essential){c.RESET}" if is_essential(top_app['app_name']) else ""
        print(f"    Heaviest:    {top_app['app_name']} ({top_app['rss_human']}){essential_marker}")

    # Cleanup opportunities
    opportunities = collect_cleanup_opportunities()
    total_reclaimable = sum(o['size'] for o in opportunities)
    safe_reclaimable = sum(o['size'] for o in opportunities if o.get('risk') == 'SAFE')
    print()
    print(f"  {c.BOLD}DISK CLEANUP{c.RESET}")
    print(f"    Reclaimable: {format_size(total_reclaimable)}")
    print(f"    Safe:        {format_size(safe_reclaimable)}")

    # Apps
    app_results = scan_applications(min_days_unused=90)
    unused_apps = [a for a in app_results['unused_apps'] if not is_essential(a['name'])]
    unused_size = sum(a['size'] for a in unused_apps)
    print()
    print(f"  {c.BOLD}APPS{c.RESET}")
    print(f"    Total:       {len(app_results['all_apps'])} apps ({format_size(app_results['total_size'])})")
    print(f"    Unused:      {len(unused_apps)} apps ({format_size(unused_size)})")

    # ==========================================================================
    # ANOMALIES
    # ==========================================================================
    classified = classify_anomalies(opportunities)
    if classified['anomalies']:
        print()
        print_header("ANOMALIES")
        for op in classified['anomalies'][:3]:
            print(f"  {c.YELLOW}[!]{c.RESET} {op['name']}: {op['size_human']} ({op.get('deviation', 0):.1f}x typical)")

    # ==========================================================================
    # TOP ACTIONS
    # ==========================================================================
    print()
    print_header("RECOMMENDED ACTIONS")

    action_num = 1

    # Quick clean if disk is low
    if disk['status'] in ('CRITICAL', 'LOW') and safe_reclaimable > 100 * 1024 * 1024:
        print(f"  {action_num}. {c.GREEN}Run quick clean{c.RESET} - reclaim {format_size(safe_reclaimable)} instantly")
        print(f"     Command: space-hog --quick-clean")
        action_num += 1

    # Unused apps
    if unused_apps:
        top_unused = unused_apps[0]
        print(f"  {action_num}. {c.YELLOW}Remove unused apps{c.RESET} - {len(unused_apps)} apps, {format_size(unused_size)}")
        print(f"     Top: {top_unused['name']} ({top_unused['size_human']}, {top_unused['days_since_used']}d unused)")
        action_num += 1

    # Anomalies
    for op in classified['anomalies'][:2]:
        print(f"  {action_num}. {c.YELLOW}Clean {op['name']}{c.RESET} - {op['size_human']}")
        print(f"     Command: {op.get('command', 'N/A')}")
        action_num += 1

    # High RAM apps (non-essential)
    for app in aggregated[:3]:
        if app['rss_bytes'] > 1024 * 1024 * 1024 and not is_essential(app['app_name']):
            print(f"  {action_num}. {c.YELLOW}Consider closing {app['app_name']}{c.RESET} - using {app['rss_human']} RAM")
            action_num += 1
            break

    # ==========================================================================
    # QUICK STATS
    # ==========================================================================
    summary = get_summary()
    regrowth = calculate_regrowth()

    if summary['total_saved'] > 0 or regrowth.get('has_data'):
        print()
        print_header("HISTORY")
        if summary['total_saved'] > 0:
            print(f"  Lifetime savings: {c.GREEN}{summary['total_saved_human']}{c.RESET} ({summary['total_cleanups']} cleanups)")
        if regrowth.get('has_data'):
            print(f"  Regrowth rate:    {regrowth.get('rate_weekly_human', 'N/A')}/week")
            print(f"  Last cleanup:     {regrowth.get('last_cleanup_date', 'N/A')} ({regrowth.get('days_since_cleanup', 0)} days ago)")

    print()
    print(f"  {c.BOLD}For more details:{c.RESET}")
    print(f"    space-hog --advise    Detailed disk cleanup recommendations")
    print(f"    space-hog --memory    RAM and process analysis")
    print(f"    space-hog --apps      Application breakdown")
    print()


def run_tier_cleanup(tier: int = 1, dry_run: bool = False):
    """Run cleanup for a specific tier."""
    from .advisor import collect_cleanup_opportunities, calculate_tier_savings
    from .stats import run_cleanup, start_cleanup_session, end_cleanup_session, print_post_cleanup_summary

    print_header(f"TIER {tier} CLEANUP" + (" (DRY RUN)" if dry_run else ""))

    # Collect opportunities and calculate tiers
    opportunities = collect_cleanup_opportunities()
    tier_savings = calculate_tier_savings(opportunities)

    if tier not in tier_savings:
        print(f"  Invalid tier: {tier}")
        return

    tier_info = tier_savings[tier]
    c = Colors

    print(f"  {c.BOLD}{tier_info['name']}{c.RESET}: {tier_info['description']}")
    print(f"  Items: {tier_info['item_count']}")
    print(f"  Potential savings: {c.GREEN}{tier_info['size_human']}{c.RESET}")
    print()

    if not tier_info['items']:
        print("  No items to clean in this tier.")
        return

    if dry_run:
        print(f"  {c.YELLOW}DRY RUN - Commands that would be executed:{c.RESET}")
        print()
        for item in tier_info['items']:
            print(f"    {item['name']}: {item['size_human']}")
            print(f"      Command: {item['command']}")
            print()
        return

    # Actually run cleanups
    session = start_cleanup_session()

    print(f"  {c.BOLD}Running cleanups...{c.RESET}")
    print()

    for item in tier_info['items']:
        print(f"  Cleaning {item['name']}...", end=' ', flush=True)
        result = run_cleanup(
            command=item['command'],
            description=item['name'],
            category=item.get('category_key', 'manual')
        )
        if result['success']:
            print(f"{c.GREEN}OK{c.RESET} ({result['bytes_freed_human']})")
            session['cleanups'].append({
                'description': item['name'],
                'freed_human': result['bytes_freed_human'],
            })
        else:
            print(f"{c.YELLOW}SKIPPED{c.RESET}")

    print()
    session = end_cleanup_session(session)
    print_post_cleanup_summary(session)


def print_smart_analysis():
    """Print smart cleanup analysis."""
    print_header("SMART ANALYSIS")
    print("  Finding DMGs, old downloads, localization waste, snapshots...\n")

    recs = get_smart_recommendations()
    c = Colors
    total_size = 0

    # DMG Installers
    dmgs = recs['dmg_installers']
    if dmgs['count'] > 0:
        total_size += dmgs['total_size']
        print(f"  {c.GREEN}{c.BOLD}DMG INSTALLER FILES{c.RESET} ({dmgs['risk']})")
        print(f"  {'-'*50}")
        print(f"  {dmgs['description']}")
        print(f"  Total: {c.BOLD}{dmgs['total_size_human']}{c.RESET} ({dmgs['count']} files)\n")
        for item in dmgs['items'][:10]:
            print(f"    {item['size_human']:>10}  {item['name']}")
        if dmgs['count'] > 10:
            print(f"    ... and {dmgs['count'] - 10} more")
        print()

    # Old Downloads
    old = recs['old_downloads']
    if old['count'] > 0:
        total_size += old['total_size']
        print(f"  {c.YELLOW}{c.BOLD}OLD DOWNLOADS (90+ days){c.RESET} ({old['risk']})")
        print(f"  {'-'*50}")
        print(f"  {old['description']}")
        print(f"  Total: {c.BOLD}{old['total_size_human']}{c.RESET} ({old['count']} items)\n")
        for item in old['items'][:10]:
            marker = '/' if item['is_dir'] else ''
            print(f"    {item['size_human']:>10}  {item['name']}{marker} ({item['days_old']} days)")
        if old['count'] > 10:
            print(f"    ... and {old['count'] - 10} more")
        print()

    # Localization
    loc = recs['localization']
    if loc['total_size'] > 0:
        total_size += loc['total_size']
        print(f"  {c.RED}{c.BOLD}UNUSED LANGUAGE FILES{c.RESET} (CAUTION)")
        print(f"  {'-'*50}")
        print(f"  Your language: {loc['primary_language']}")
        print(f"  Unused .lproj folders in /Applications")
        print(f"  Total: {c.BOLD}{loc['total_size_human']}{c.RESET}")
        print(f"  Note: {loc['note']}")
        print()

    # Time Machine
    tm = recs['time_machine_snapshots']
    if tm['snapshot_count'] > 0:
        total_size += tm['estimated_size']
        print(f"  {c.YELLOW}{c.BOLD}TIME MACHINE SNAPSHOTS{c.RESET} (MODERATE)")
        print(f"  {'-'*50}")
        print(f"  Local snapshots: {tm['snapshot_count']}")
        print(f"  Estimated size: ~{tm['estimated_size_human']}")
        print(f"  Command: {tm['command']}")
        print(f"  Note: {tm['note']}")
        print()

    # Summary
    print_header("SUMMARY")
    print(f"  Total smart findings: {c.BOLD}{format_size(total_size)}{c.RESET}")
    print()
    print("  Safe to delete:")
    if dmgs['count'] > 0:
        print(f"    rm ~/Downloads/*.dmg ~/Desktop/*.dmg")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Space Hog - Find wasted space on your Mac',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  space-hog                     # Scan home directory
  space-hog /path/to/scan       # Scan specific directory
  space-hog --min-size 50       # Only show items > 50MB
  space-hog --duplicates        # Include duplicate file scan
  space-hog --caches-only       # Only check cache locations
  space-hog --advise            # Prioritized cleanup recommendations
  space-hog --smart             # Smart analysis (DMGs, old downloads, etc.)
  space-hog --dry-run           # Preview deletions without executing
  space-hog --docker            # Docker deep-dive (VM bloat, volumes)
  space-hog --apps              # Find unused/AI-replaceable apps
  space-hog --stats             # Show cleanup history and savings
  space-hog --regrowth          # Show regrowth tracking and recommendations
  space-hog --quick-clean       # Run safe tier 1 cleanup
  space-hog --run-tier 2        # Run tier 2 cleanup (Docker + safe)
  space-hog --run-tier 2 --dry-run  # Preview tier 2 cleanup
  space-hog --memory            # Analyze RAM usage and autostart items
  space-hog --prefs             # Show user preferences
  space-hog --essential Comet   # Mark Comet as essential (never remove)
  space-hog --blacklist Rewind  # Mark Rewind as always removable
  space-hog --full              # Complete system health report

Currently scans:
  - Trash, Downloads (old files, DMGs)
  - Caches: npm, yarn, pnpm, bun, pip, cargo, gradle, maven
  - AI tools: Ollama models, Codeium, Gemini CLI, Claude Code
  - Docker: images, containers, volumes, VM disk bloat
  - Xcode: DerivedData, archives, device symbols, simulators
  - Dev dirs: node_modules, .git, venv, DerivedData, Pods
  - Applications: unused apps, AI-replaceable apps
  - iOS backups, Mail attachments, Log files
  - Time Machine local snapshots
  - Large files, duplicates
        """
    )
    parser.add_argument('path', nargs='?', default=str(Path.home()),
                        help='Directory to scan (default: home directory)')
    parser.add_argument('--min-size', type=int, default=100,
                        help='Minimum size in MB to report (default: 100)')
    parser.add_argument('--duplicates', '-d', action='store_true',
                        help='Scan for duplicate files (slower)')
    parser.add_argument('--caches-only', '-c', action='store_true',
                        help='Only check cache locations')
    parser.add_argument('--large-files', '-l', action='store_true',
                        help='Only find large files')
    parser.add_argument('--hogs-only', '-g', action='store_true',
                        help='Only find space hog directories')
    parser.add_argument('--cleanup-guide', action='store_true',
                        help='Show detailed cleanup guide with safety info')
    parser.add_argument('--advise', '-a', action='store_true',
                        help='AI-powered prioritized cleanup recommendations')
    parser.add_argument('--docker', action='store_true',
                        help='Detailed Docker disk analysis (VM bloat, images, volumes)')
    parser.add_argument('--apps', action='store_true',
                        help='Analyze applications (unused, AI-replaceable)')
    parser.add_argument('--stats', action='store_true',
                        help='Show cleanup history and total space saved')
    parser.add_argument('--days-unused', type=int, default=90,
                        help='Days threshold for unused apps (default: 90)')
    parser.add_argument('--smart', '-s', action='store_true',
                        help='Smart analysis (DMGs, old downloads, localization, snapshots)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be deleted without actually deleting')
    parser.add_argument('--regrowth', action='store_true',
                        help='Show regrowth tracking and cleanup frequency recommendations')
    parser.add_argument('--quick-clean', action='store_true',
                        help='Run tier 1 cleanup (safe caches + trash)')
    parser.add_argument('--run-tier', type=int, choices=[1, 2, 3],
                        help='Run cleanup tier 1-3 (use with --dry-run to preview)')
    parser.add_argument('--memory', '-m', action='store_true',
                        help='Analyze RAM usage, autostart items, and background processes')
    parser.add_argument('--prefs', action='store_true',
                        help='Show user preferences (essential/blacklist apps)')
    parser.add_argument('--essential', type=str, metavar='APP',
                        help='Mark an app as essential (never suggest removing)')
    parser.add_argument('--blacklist', type=str, metavar='APP',
                        help='Mark an app as removable (always suggest removing)')
    parser.add_argument('--unused', '-u', action='store_true',
                        help='Detect unused software (apps, brew packages, orphan deps)')
    parser.add_argument('--full', '-f', action='store_true',
                        help='Full system health report (disk + memory + apps + recommendations)')

    args = parser.parse_args()

    # Handle special modes
    if args.docker:
        print("\nSpace Hog - Docker Analysis")
        print_docker_analysis()
        sys.exit(0)

    if args.advise:
        print("\nSpace Hog - Advisor")
        print_advise()
        sys.exit(0)

    if args.cleanup_guide:
        print("\nSpace Hog - Cleanup Guide")
        print_cleanup_guide()
        sys.exit(0)

    if args.apps:
        print("\nSpace Hog - Applications Analysis")
        print_applications_analysis(min_days_unused=args.days_unused)
        sys.exit(0)

    if args.stats:
        print("\nSpace Hog - Statistics")
        print_stats()
        sys.exit(0)

    if args.smart:
        print("\nSpace Hog - Smart Analysis")
        print_smart_analysis()
        sys.exit(0)

    if args.regrowth:
        print("\nSpace Hog - Regrowth Tracking")
        print_regrowth_report()
        sys.exit(0)

    if args.quick_clean or args.run_tier:
        run_tier_cleanup(
            tier=args.run_tier or 1,
            dry_run=args.dry_run
        )
        sys.exit(0)

    if args.unused:
        print("\nSpace Hog - Unused Software Detection")
        print_unused_report(min_days=args.days_unused)
        sys.exit(0)

    if args.memory:
        print("\nSpace Hog - Memory Analysis")
        print_memory_analysis()
        sys.exit(0)

    if args.prefs:
        print("\nSpace Hog - Preferences")
        print_preferences()
        sys.exit(0)

    if args.essential:
        add_essential_app(args.essential)
        print(f"Marked '{args.essential}' as essential (will never suggest removing)")
        sys.exit(0)

    if args.blacklist:
        add_blacklist_app(args.blacklist)
        print(f"Marked '{args.blacklist}' as blacklisted (will always suggest removing)")
        sys.exit(0)

    if args.full:
        print("\nSpace Hog - Full System Health Report")
        print_full_report()
        sys.exit(0)

    # Standard scanning modes
    root = Path(args.path).expanduser().resolve()

    if not root.exists():
        print(f"Error: Path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    print(f"\nSpace Hog - Scanning for wasted space...")
    print(f"Root: {root}")

    if args.caches_only:
        print_header("CACHES")
        caches = check_caches()
        for path, size, desc in caches:
            print(f"  {format_size(size):>10}  {desc}")
            print(f"             {path}")
        print(f"\n  Total: {format_size(sum(c[1] for c in caches))}")
    elif args.large_files:
        print_header(f"LARGE FILES (>{args.min_size}MB)")
        large_files = list(find_large_files(root, min_size_mb=args.min_size))
        large_files.sort(key=lambda x: x.size, reverse=True)
        for f in large_files:
            print(f"  {f.size_human:>10}  {f.path}")
    elif args.hogs_only:
        print_header(f"SPACE HOGS (>{args.min_size}MB)")
        hogs = find_space_hogs(root, min_size_mb=args.min_size)
        for path, size, desc in hogs:
            print(f"  {format_size(size):>10}  {desc}")
            print(f"             {path}")
    else:
        scan_all(root, args)


if __name__ == '__main__':
    main()
