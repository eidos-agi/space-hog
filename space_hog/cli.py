"""CLI entry point for Space Hog."""

import sys
import argparse
from pathlib import Path

from .utils import format_size, print_header
from .caches import check_caches
from .scanners import find_large_files, find_space_hogs
from .docker import print_docker_analysis
from .advisor import print_advise, print_cleanup_guide
from .applications import print_applications_analysis
from .stats import print_stats
from .runner import scan_all


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
  space-hog --docker            # Docker deep-dive (VM bloat, volumes)
  space-hog --apps              # Find unused/AI-replaceable apps
  space-hog --stats             # Show cleanup history and savings

Currently scans:
  - Trash, Downloads (old files)
  - Caches: npm, yarn, pip, Library/Caches, ~/.cache
  - Docker: images, containers, volumes, VM disk bloat
  - Dev dirs: node_modules, .git, venv, DerivedData, Pods
  - Applications: unused apps, AI-replaceable apps
  - Large files, duplicates

Planned features (see TODO.md):
  - Xcode: DerivedData, archives, device support
  - Homebrew: old versions, cache
  - JetBrains IDEs: caches, logs
  - Time Machine local snapshots
  - Slack, Spotify, Zoom caches
  - Interactive cleanup wizard
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
