"""Main scan runner for Space Hog."""

from pathlib import Path

from .utils import format_size, print_header
from .scanners import find_large_files, find_space_hogs, find_duplicates
from .caches import check_caches, get_trash_size, get_downloads_analysis


def scan_all(root: Path, args):
    """Run all scans and display results."""
    total_reclaimable = 0

    # Trash
    print_header("TRASH")
    trash_size = get_trash_size()
    if trash_size > 0:
        print(f"  Trash: {format_size(trash_size)}")
        print(f"  Clean with: rm -rf ~/.Trash/*")
        total_reclaimable += trash_size
    else:
        print("  Trash is empty")

    # Downloads
    print_header("DOWNLOADS (files older than 30 days)")
    downloads_size, old_downloads = get_downloads_analysis()
    if downloads_size > 0:
        print(f"  Total old files: {format_size(downloads_size)} ({len(old_downloads)} files)")
        for f in old_downloads[:5]:
            print(f"    {f.size_human:>10}  {f.path.name}")
        if len(old_downloads) > 5:
            print(f"    ... and {len(old_downloads) - 5} more files")
        total_reclaimable += downloads_size
    else:
        print("  No old files in Downloads")

    # Caches
    print_header("CACHES")
    caches = check_caches()
    cache_total = sum(c[1] for c in caches)
    if caches:
        for path, size, desc in caches[:10]:
            print(f"  {format_size(size):>10}  {desc}")
            print(f"             {path}")
        if len(caches) > 10:
            print(f"  ... and {len(caches) - 10} more cache locations")
        print(f"\n  Total cache size: {format_size(cache_total)}")
        total_reclaimable += cache_total
    else:
        print("  No significant caches found")

    # Space hogs in specified directory
    print_header(f"SPACE HOGS IN {root}")
    hogs = find_space_hogs(root, min_size_mb=args.min_size)
    hog_total = sum(h[1] for h in hogs)
    if hogs:
        for path, size, desc in hogs[:15]:
            print(f"  {format_size(size):>10}  {desc}")
            print(f"             {path}")
        if len(hogs) > 15:
            print(f"  ... and {len(hogs) - 15} more directories")
        print(f"\n  Total: {format_size(hog_total)}")
        total_reclaimable += hog_total
    else:
        print(f"  No space hogs found (>{args.min_size}MB)")

    # Large files
    print_header(f"LARGE FILES (>{args.min_size}MB)")
    large_files = list(find_large_files(root, min_size_mb=args.min_size))
    large_files.sort(key=lambda x: x.size, reverse=True)
    if large_files:
        for f in large_files[:15]:
            print(f"  {f.size_human:>10}  {f.path}")
        if len(large_files) > 15:
            print(f"  ... and {len(large_files) - 15} more files")
    else:
        print(f"  No files found larger than {args.min_size}MB")

    # Duplicates (optional)
    if args.duplicates:
        print_header("DUPLICATE FILES")
        print("  Scanning for duplicates (this may take a while)...")
        duplicates = find_duplicates(root, min_size_mb=args.min_size)
        if duplicates:
            dup_total = 0
            for file_hash, files in list(duplicates.items())[:10]:
                size = files[0].stat().st_size
                wasted = size * (len(files) - 1)
                dup_total += wasted
                print(f"\n  {format_size(size)} x {len(files)} copies ({format_size(wasted)} wasted):")
                for f in files[:3]:
                    print(f"    {f}")
                if len(files) > 3:
                    print(f"    ... and {len(files) - 3} more")
            print(f"\n  Total wasted by duplicates: {format_size(dup_total)}")
            total_reclaimable += dup_total
        else:
            print(f"  No duplicates found (>{args.min_size}MB)")

    # Summary
    print_header("SUMMARY")
    print(f"  Potentially reclaimable space: {format_size(total_reclaimable)}")
    print()
    print("  Run 'space-hog --advise' for prioritized cleanup recommendations.")
    print("  Run 'space-hog --apps' to find unused/AI-replaceable applications.")
    print()
