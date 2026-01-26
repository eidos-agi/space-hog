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
from .stats import print_stats
from .runner import scan_all
from .smart import get_smart_recommendations


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
  space-hog --docker            # Docker deep-dive (VM bloat, volumes)
  space-hog --apps              # Find unused/AI-replaceable apps
  space-hog --stats             # Show cleanup history and savings

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
