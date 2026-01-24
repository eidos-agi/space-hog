#!/usr/bin/env python3
"""
Space Hog - Find wasted space on your Mac

A CLI tool that identifies large files, caches, duplicates, and cleanup opportunities.
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Generator
import subprocess
import json as json_module


@dataclass
class FileInfo:
    path: Path
    size: int

    @property
    def size_human(self) -> str:
        return format_size(self.size)


def format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_dir_size(path: Path) -> int:
    """Calculate total size of a directory."""
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file() and not entry.is_symlink():
                try:
                    total += entry.stat().st_size
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass
    return total


def find_large_files(root: Path, min_size_mb: int = 100) -> Generator[FileInfo, None, None]:
    """Find files larger than min_size_mb."""
    min_size = min_size_mb * 1024 * 1024
    try:
        for entry in root.rglob('*'):
            if entry.is_file() and not entry.is_symlink():
                try:
                    size = entry.stat().st_size
                    if size >= min_size:
                        yield FileInfo(entry, size)
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass


# Common space hogs on macOS
SPACE_HOG_PATTERNS = {
    'node_modules': 'Node.js dependencies',
    '.git': 'Git repositories',
    '__pycache__': 'Python cache',
    '.pytest_cache': 'Pytest cache',
    'venv': 'Python virtual environments',
    '.venv': 'Python virtual environments',
    'env': 'Python virtual environments',
    '.tox': 'Tox testing environments',
    'target': 'Rust/Maven build artifacts',
    'build': 'Build directories',
    'dist': 'Distribution directories',
    '.gradle': 'Gradle cache',
    '.cargo': 'Cargo cache',
    'Pods': 'CocoaPods dependencies',
    'DerivedData': 'Xcode derived data',
    '.nuget': 'NuGet packages',
    'vendor': 'Vendor dependencies',
}

CACHE_LOCATIONS = [
    ('~/Library/Caches', 'Application caches'),
    ('~/Library/Application Support/Code/Cache', 'VS Code cache'),
    ('~/Library/Application Support/Code/CachedData', 'VS Code cached data'),
    ('~/Library/Application Support/Slack/Cache', 'Slack cache'),
    ('~/Library/Application Support/discord/Cache', 'Discord cache'),
    ('~/Library/Application Support/Google/Chrome/Default/Cache', 'Chrome cache'),
    ('~/Library/Developer/Xcode/DerivedData', 'Xcode derived data'),
    ('~/Library/Developer/Xcode/Archives', 'Xcode archives'),
    ('~/Library/Developer/CoreSimulator', 'iOS Simulators'),
    ('~/.npm', 'NPM cache'),
    ('~/.yarn/cache', 'Yarn cache'),
    ('~/.cache', 'General cache'),
    ('~/.docker', 'Docker data'),
    ('~/Library/Containers/com.docker.docker', 'Docker Desktop'),
]

# Maps cache paths to their cleanup info keys
CACHE_TO_CLEANUP = {
    '~/.Trash': 'trash',
    '~/.npm': 'npm',
    '~/.yarn/cache': 'yarn',
    '~/Library/Caches': 'library_caches',
    '~/.cache': 'dot_cache',
    '~/Library/Developer/CoreSimulator': 'simulators',
    '~/Library/Developer/Xcode/DerivedData': 'xcode_derived',
    '~/Library/Containers/com.docker.docker': 'docker',
    '~/.docker': 'docker',
}

# Cleanup commands with safety information
CLEANUP_INFO = {
    'trash': {
        'command': 'rm -rf ~/.Trash/*',
        'name': 'Empty Trash',
        'risk': 'SAFE',
        'risk_score': 1,  # Lower = safer, prioritize first
        'description': 'Permanently deletes files already in your Trash.',
        'side_effects': ['Files cannot be recovered after this'],
        'recommendation': 'Safe to run. Review Trash contents first if unsure.',
    },
    'npm': {
        'command': 'npm cache clean --force',
        'name': 'Clear NPM Cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes cached npm packages. NPM self-heals since v5.',
        'side_effects': [
            'Next npm install will re-download packages (slightly slower)',
            'No impact on installed node_modules',
        ],
        'recommendation': 'Safe to run. Try "npm cache verify" first for a gentler approach.',
    },
    'docker': {
        'command': 'docker system prune -a',
        'name': 'Clear Docker',
        'risk': 'MODERATE',
        'risk_score': 2,
        'description': 'Removes stopped containers, unused networks, and ALL unused images.',
        'side_effects': [
            'Must re-pull/rebuild images not currently in use',
            'Build cache cleared (slower first builds)',
            'Does NOT delete volumes (data is safe)',
            'NOTE: VM disk (Docker.raw) does NOT shrink automatically!',
        ],
        'recommendation': 'Safe for dev machines. To reclaim VM disk space: Docker Desktop → Settings → Resources → reduce Virtual disk limit, or factory reset.',
    },
    'library_caches': {
        'command': 'rm -rf ~/Library/Caches/*',
        'name': 'Clear User Caches',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes application cache files. macOS regenerates them automatically.',
        'side_effects': [
            'Apps may be slower on first launch while rebuilding cache',
            'May need to re-login to some apps',
            'Some apps store non-cache data here (rare)',
        ],
        'recommendation': 'Generally safe. Consider backing up first if concerned.',
    },
    'dot_cache': {
        'command': 'rm -rf ~/.cache/*',
        'name': 'Clear ~/.cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes general cache directory used by CLI tools and apps.',
        'side_effects': [
            'Tools rebuild caches on next use',
            'May need to re-authenticate some CLI tools',
        ],
        'recommendation': 'Safe to run. Data regenerates automatically.',
    },
    'simulators': {
        'command': 'xcrun simctl delete unavailable',
        'name': 'Delete Unavailable iOS Simulators',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes simulators incompatible with current Xcode version.',
        'side_effects': ['Only removes simulators you cannot use anyway'],
        'recommendation': 'Safe to run. Also try "xcrun simctl runtime delete unavailable" for runtimes.',
    },
    'xcode_derived': {
        'command': 'rm -rf ~/Library/Developer/Xcode/DerivedData/*',
        'name': 'Clear Xcode DerivedData',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes Xcode build artifacts and indexes.',
        'side_effects': [
            'Next build will be slower (full rebuild)',
            'Xcode will re-index projects',
        ],
        'recommendation': 'Safe to run. Common fix for Xcode build issues.',
    },
    'yarn': {
        'command': 'yarn cache clean',
        'name': 'Clear Yarn Cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes cached yarn packages.',
        'side_effects': ['Next yarn install will re-download packages'],
        'recommendation': 'Safe to run.',
    },
}

# Legacy list format for --cleanup-guide (kept for backwards compatibility)
CLEANUP_COMMANDS = [
    {
        'command': 'rm -rf ~/.Trash/*',
        'name': 'Empty Trash',
        'risk': 'SAFE',
        'description': 'Permanently deletes files already in your Trash.',
        'side_effects': [
            'Files cannot be recovered after this',
        ],
        'recommendation': 'Safe to run. Review Trash contents first if unsure.',
    },
    {
        'command': 'npm cache clean --force',
        'name': 'Clear NPM Cache',
        'risk': 'SAFE',
        'description': 'Removes cached npm packages. NPM self-heals since v5.',
        'side_effects': [
            'Next npm install will re-download packages (slightly slower)',
            'No impact on installed node_modules',
        ],
        'recommendation': 'Safe to run. Try "npm cache verify" first for a gentler approach.',
    },
    {
        'command': 'docker system prune -a',
        'name': 'Clear Docker',
        'risk': 'MODERATE',
        'description': 'Removes stopped containers, unused networks, and ALL unused images.',
        'side_effects': [
            'Must re-pull/rebuild images not currently in use',
            'Build cache cleared (slower first builds)',
            'Does NOT delete volumes (data is safe)',
        ],
        'recommendation': 'Safe for dev machines. Use "docker system prune" (no -a) to keep tagged images.',
    },
    {
        'command': 'rm -rf ~/Library/Caches/*',
        'name': 'Clear User Caches',
        'risk': 'SAFE',
        'description': 'Removes application cache files. macOS regenerates them automatically.',
        'side_effects': [
            'Apps may be slower on first launch while rebuilding cache',
            'May need to re-login to some apps',
            'Some apps store non-cache data here (rare)',
        ],
        'recommendation': 'Generally safe. Consider backing up first if concerned.',
    },
    {
        'command': 'rm -rf ~/.cache/*',
        'name': 'Clear ~/.cache',
        'risk': 'SAFE',
        'description': 'Removes general cache directory used by CLI tools and apps.',
        'side_effects': [
            'Tools rebuild caches on next use',
            'May need to re-authenticate some CLI tools',
        ],
        'recommendation': 'Safe to run. Data regenerates automatically.',
    },
    {
        'command': 'xcrun simctl delete unavailable',
        'name': 'Delete Unavailable iOS Simulators',
        'risk': 'SAFE',
        'description': 'Removes simulators incompatible with current Xcode version.',
        'side_effects': [
            'Only removes simulators you cannot use anyway',
        ],
        'recommendation': 'Safe to run. Also try "xcrun simctl runtime delete unavailable" for runtimes.',
    },
    {
        'command': 'rm -rf ~/Library/Developer/Xcode/DerivedData/*',
        'name': 'Clear Xcode DerivedData',
        'risk': 'SAFE',
        'description': 'Removes Xcode build artifacts and indexes.',
        'side_effects': [
            'Next build will be slower (full rebuild)',
            'Xcode will re-index projects',
        ],
        'recommendation': 'Safe to run. Common fix for Xcode build issues.',
    },
    {
        'command': 'yarn cache clean',
        'name': 'Clear Yarn Cache',
        'risk': 'SAFE',
        'description': 'Removes cached yarn packages.',
        'side_effects': [
            'Next yarn install will re-download packages',
        ],
        'recommendation': 'Safe to run.',
    },
]


def find_space_hogs(root: Path, min_size_mb: int = 50) -> list[tuple[Path, int, str]]:
    """Find common space-hogging directories."""
    results = []
    min_size = min_size_mb * 1024 * 1024

    for pattern, description in SPACE_HOG_PATTERNS.items():
        try:
            for entry in root.rglob(pattern):
                if entry.is_dir():
                    try:
                        size = get_dir_size(entry)
                        if size >= min_size:
                            results.append((entry, size, description))
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass

    return sorted(results, key=lambda x: x[1], reverse=True)


def check_caches() -> list[tuple[Path, int, str]]:
    """Check common cache locations."""
    results = []

    for location, description in CACHE_LOCATIONS:
        path = Path(location).expanduser()
        if path.exists():
            try:
                size = get_dir_size(path)
                if size > 0:
                    results.append((path, size, description))
            except (PermissionError, OSError):
                pass

    return sorted(results, key=lambda x: x[1], reverse=True)


def find_duplicates(root: Path, min_size_mb: int = 10) -> dict[str, list[Path]]:
    """Find duplicate files by comparing file sizes and hashes."""
    min_size = min_size_mb * 1024 * 1024

    # Group by size first
    size_groups = defaultdict(list)
    try:
        for entry in root.rglob('*'):
            if entry.is_file() and not entry.is_symlink():
                try:
                    size = entry.stat().st_size
                    if size >= min_size:
                        size_groups[size].append(entry)
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass

    # For groups with same size, compute hash
    duplicates = defaultdict(list)
    for size, files in size_groups.items():
        if len(files) < 2:
            continue

        for filepath in files:
            try:
                file_hash = hash_file(filepath)
                duplicates[file_hash].append(filepath)
            except (PermissionError, OSError):
                pass

    # Filter to only actual duplicates
    return {h: files for h, files in duplicates.items() if len(files) > 1}


def hash_file(filepath: Path, chunk_size: int = 8192) -> str:
    """Compute MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_trash_size() -> int:
    """Get size of Trash folder."""
    trash_path = Path.home() / '.Trash'
    if trash_path.exists():
        return get_dir_size(trash_path)
    return 0


def get_downloads_analysis(min_age_days: int = 30) -> tuple[int, list[FileInfo]]:
    """Analyze Downloads folder for old files."""
    downloads = Path.home() / 'Downloads'
    if not downloads.exists():
        return 0, []

    import time
    cutoff = time.time() - (min_age_days * 24 * 60 * 60)
    old_files = []
    total_size = 0

    try:
        for entry in downloads.iterdir():
            if entry.is_file() and not entry.is_symlink():
                try:
                    stat = entry.stat()
                    if stat.st_mtime < cutoff:
                        old_files.append(FileInfo(entry, stat.st_size))
                        total_size += stat.st_size
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass

    return total_size, sorted(old_files, key=lambda x: x.size, reverse=True)


def analyze_docker() -> dict:
    """Analyze Docker disk usage including VM disk bloat."""
    result = {
        'installed': False,
        'running': False,
        'vm_disk_path': None,
        'vm_disk_allocated': 0,
        'vm_disk_used': 0,
        'vm_disk_bloat': 0,
        'images': {'count': 0, 'size': 0, 'reclaimable': 0},
        'containers': {'count': 0, 'size': 0, 'reclaimable': 0},
        'volumes': {'count': 0, 'size': 0, 'reclaimable': 0},
        'build_cache': {'size': 0, 'reclaimable': 0},
        'total_usage': 0,
        'total_reclaimable': 0,
    }

    # Check if Docker is installed
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        result['installed'] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return result

    # Check VM disk file (Docker Desktop on Mac)
    vm_disk_path = Path.home() / 'Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw'
    if vm_disk_path.exists():
        result['vm_disk_path'] = str(vm_disk_path)
        # Logical size (what ls shows)
        result['vm_disk_logical'] = vm_disk_path.stat().st_size
        # Actual disk usage (sparse file - what du shows)
        try:
            du_output = subprocess.run(
                ['du', '-k', str(vm_disk_path)],
                capture_output=True, text=True, timeout=10
            )
            if du_output.returncode == 0:
                result['vm_disk_allocated'] = int(du_output.stdout.split()[0]) * 1024
            else:
                result['vm_disk_allocated'] = result['vm_disk_logical']
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            result['vm_disk_allocated'] = result['vm_disk_logical']

    # Check if Docker daemon is running
    try:
        subprocess.run(['docker', 'info'], capture_output=True, check=True, timeout=5)
        result['running'] = True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return result

    # Get Docker disk usage
    try:
        df_output = subprocess.run(
            ['docker', 'system', 'df', '--format', '{{json .}}'],
            capture_output=True, text=True, check=True, timeout=30
        )
        for line in df_output.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json_module.loads(line)
                type_name = data.get('Type', '').lower()

                # Parse size strings like "1.592GB", "40.96kB", or "-4.826e+08B"
                def parse_size(size_str):
                    if not size_str or size_str == '0B':
                        return 0
                    size_str = size_str.strip()

                    # Handle scientific notation like "-4.826e+08B"
                    if 'e' in size_str.lower():
                        # Extract the number before 'B'
                        if size_str.upper().endswith('B'):
                            try:
                                return max(0, int(float(size_str[:-1])))
                            except ValueError:
                                return 0

                    multipliers = {
                        'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4,
                        'KIB': 1024, 'MIB': 1024**2, 'GIB': 1024**3, 'TIB': 1024**4,
                    }
                    size_upper = size_str.upper()
                    for unit, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
                        if size_upper.endswith(unit):
                            try:
                                num_str = size_str[:-len(unit)]
                                return max(0, int(float(num_str) * mult))
                            except ValueError:
                                return 0
                    # Try parsing as just a number
                    try:
                        return max(0, int(float(size_str)))
                    except ValueError:
                        return 0

                size = parse_size(data.get('Size', '0B'))
                reclaimable_str = data.get('Reclaimable', '0B')
                # Handle format like "312.7MB (100%)"
                if '(' in reclaimable_str:
                    reclaimable_str = reclaimable_str.split('(')[0].strip()
                reclaimable = parse_size(reclaimable_str)

                if 'image' in type_name:
                    result['images'] = {
                        'count': int(data.get('TotalCount', 0)),
                        'size': size,
                        'reclaimable': reclaimable,
                    }
                elif 'container' in type_name:
                    result['containers'] = {
                        'count': int(data.get('TotalCount', 0)),
                        'size': size,
                        'reclaimable': reclaimable,
                    }
                elif 'volume' in type_name:
                    result['volumes'] = {
                        'count': int(data.get('TotalCount', 0)),
                        'size': size,
                        'reclaimable': reclaimable,
                    }
                elif 'build' in type_name:
                    result['build_cache'] = {
                        'size': size,
                        'reclaimable': reclaimable,
                    }
            except json_module.JSONDecodeError:
                continue

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    # Calculate totals
    result['total_usage'] = (
        result['images']['size'] +
        result['containers']['size'] +
        result['volumes']['size'] +
        result['build_cache']['size']
    )
    result['total_reclaimable'] = (
        result['images']['reclaimable'] +
        result['containers']['reclaimable'] +
        result['volumes']['reclaimable'] +
        result['build_cache']['reclaimable']
    )

    # Calculate VM disk bloat
    if result['vm_disk_allocated'] > 0:
        result['vm_disk_used'] = result['total_usage']
        result['vm_disk_bloat'] = result['vm_disk_allocated'] - result['total_usage']

    return result


def analyze_docker_volumes() -> list[dict]:
    """Get detailed volume information including project associations."""
    volumes = []

    try:
        # Get verbose docker system df which includes volume details
        df_output = subprocess.run(
            ['docker', 'system', 'df', '-v', '--format', '{{json .}}'],
            capture_output=True, text=True, check=True, timeout=30
        )

        data = json_module.loads(df_output.stdout)
        volume_list = data.get('Volumes', [])

        for vol in volume_list:
            labels = vol.get('Labels', '')
            # Parse project from labels
            project = None
            if 'com.supabase.cli.project=' in labels:
                for part in labels.split(','):
                    if 'com.supabase.cli.project=' in part:
                        project = part.split('=')[1]
                        break
            elif 'com.docker.compose.project=' in labels:
                for part in labels.split(','):
                    if 'com.docker.compose.project=' in part:
                        project = part.split('=')[1]
                        break

            # Parse size
            size_str = vol.get('Size', '0B')
            size = 0
            multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
            for unit, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
                if size_str.upper().endswith(unit):
                    try:
                        size = int(float(size_str[:-len(unit)]) * mult)
                    except ValueError:
                        pass
                    break

            links = int(vol.get('Links', 0))

            volumes.append({
                'name': vol.get('Name', ''),
                'project': project,
                'size': size,
                'size_human': format_size(size),
                'links': links,
                'in_use': links > 0,
                'driver': vol.get('Driver', 'local'),
            })

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json_module.JSONDecodeError):
        pass

    return sorted(volumes, key=lambda x: -x['size'])


def print_docker_analysis():
    """Print detailed Docker disk analysis."""
    print_header("DOCKER DISK ANALYSIS")

    docker = analyze_docker()

    if not docker['installed']:
        print("  Docker is not installed.")
        return

    if not docker['running']:
        print("  Docker daemon is not running.")
        print("  Start Docker Desktop to analyze disk usage.")
        if docker['vm_disk_allocated'] > 0:
            print(f"\n  VM disk allocated: {format_size(docker['vm_disk_allocated'])}")
            print(f"  Path: {docker['vm_disk_path']}")
        return

    green = '\033[92m'
    yellow = '\033[93m'
    red = '\033[91m'
    bold = '\033[1m'
    reset = '\033[0m'

    # VM Disk analysis
    if docker['vm_disk_allocated'] > 0:
        vm_logical = docker.get('vm_disk_logical', docker['vm_disk_allocated'])
        vm_actual = docker['vm_disk_allocated']
        vm_objects = docker['vm_disk_used']
        vm_overhead = vm_actual - vm_objects if vm_actual > vm_objects else 0

        print(f"  {bold}VM DISK (Docker.raw){reset}")
        print(f"  {'-'*50}")
        print(f"  Max size (logical):     {format_size(vm_logical)}")
        print(f"  Actual disk usage:      {format_size(vm_actual)}")
        print(f"  Docker objects inside:  {format_size(vm_objects)}")

        if vm_overhead > 1024 * 1024 * 1024:  # > 1GB overhead
            overhead_pct = (vm_overhead / vm_actual) * 100 if vm_actual > 0 else 0
            print(f"  {yellow}VM overhead/deleted:     {format_size(vm_overhead)} ({overhead_pct:.0f}% of disk){reset}")
            print()
            print(f"  {yellow}The {format_size(vm_overhead)} gap is from deleted images/containers")
            print(f"  that were removed inside Docker but the disk file never shrinks.{reset}")
        print()

    # Docker objects breakdown
    print(f"  {bold}DOCKER OBJECTS{reset}")
    print(f"  {'-'*50}")
    print(f"  {'Type':<15} {'Count':<8} {'Size':<12} {'Reclaimable':<12}")
    print(f"  {'-'*50}")

    for obj_type, data in [
        ('Images', docker['images']),
        ('Containers', docker['containers']),
        ('Volumes', docker['volumes']),
        ('Build Cache', docker['build_cache']),
    ]:
        count = data.get('count', '-')
        size = format_size(data['size'])
        reclaimable = format_size(data['reclaimable'])
        print(f"  {obj_type:<15} {str(count):<8} {size:<12} {reclaimable:<12}")

    print(f"  {'-'*50}")
    print(f"  {'TOTAL':<15} {'':<8} {format_size(docker['total_usage']):<12} {format_size(docker['total_reclaimable']):<12}")
    print()

    # Recommendations
    print(f"  {bold}RECOMMENDATIONS{reset}")
    print(f"  {'-'*50}")

    if docker['total_reclaimable'] > 100 * 1024 * 1024:  # > 100MB
        print(f"  {green}1. Prune unused objects:{reset}")
        print(f"     docker system prune -a")
        print(f"     (Reclaims ~{format_size(docker['total_reclaimable'])})")
        print()

    if docker['volumes']['reclaimable'] > 50 * 1024 * 1024:  # > 50MB
        print(f"  {yellow}2. Remove unused volumes (check first!):{reset}")
        print(f"     docker volume prune")
        print(f"     (Reclaims ~{format_size(docker['volumes']['reclaimable'])})")
        print()

    vm_overhead = docker['vm_disk_allocated'] - docker['vm_disk_used']
    if vm_overhead > 5 * 1024 * 1024 * 1024:  # > 5GB overhead
        print(f"  {red}3. Reclaim VM overhead ({format_size(vm_overhead)}):{reset}")
        print(f"     Option A: Docker Desktop → Settings → Resources")
        print(f"               → Reduce 'Virtual disk limit'")
        print(f"     Option B: Factory reset Docker Desktop")
        print(f"     Option C: Stop Docker, delete Docker.raw, restart")
        print()

    # Volume details
    volumes = analyze_docker_volumes()
    if volumes:
        print(f"  {bold}VOLUMES BY PROJECT{reset}")
        print(f"  {'-'*50}")

        # Group by project
        projects = {}
        orphaned = []
        for vol in volumes:
            proj = vol.get('project') or 'unknown'
            if vol['links'] == 0 and proj not in ('unknown',):
                orphaned.append(vol)
            if proj not in projects:
                projects[proj] = {'volumes': [], 'total_size': 0}
            projects[proj]['volumes'].append(vol)
            projects[proj]['total_size'] += vol['size']

        # Sort projects by size
        for proj, data in sorted(projects.items(), key=lambda x: -x[1]['total_size']):
            in_use_marker = ''
            vol_count = len(data['volumes'])
            orphan_count = sum(1 for v in data['volumes'] if v['links'] == 0)
            if orphan_count == vol_count:
                in_use_marker = f' {yellow}(orphaned){reset}'
            elif orphan_count > 0:
                in_use_marker = f' {yellow}({orphan_count} orphaned){reset}'

            print(f"  {proj:<25} {format_size(data['total_size']):>10} ({vol_count} volumes){in_use_marker}")

        print()
        if orphaned:
            orphan_size = sum(v['size'] for v in orphaned)
            print(f"  {yellow}Orphaned volumes (no running containers): {format_size(orphan_size)}{reset}")
            print(f"  To remove orphaned volumes for a project:")
            print(f"    docker volume rm $(docker volume ls -q -f 'label=com.docker.compose.project=PROJECT_NAME')")
            print()

    # JSON output for AI
    print()
    print(f"  {bold}STRUCTURED DATA{reset}")
    print(f"  {'-'*50}")
    vm_overhead = docker['vm_disk_allocated'] - docker['vm_disk_used']
    summary = {
        'vm_disk_logical_bytes': docker.get('vm_disk_logical', docker['vm_disk_allocated']),
        'vm_disk_logical_human': format_size(docker.get('vm_disk_logical', docker['vm_disk_allocated'])),
        'vm_disk_actual_bytes': docker['vm_disk_allocated'],
        'vm_disk_actual_human': format_size(docker['vm_disk_allocated']),
        'vm_disk_objects_bytes': docker['vm_disk_used'],
        'vm_disk_objects_human': format_size(docker['vm_disk_used']),
        'vm_disk_overhead_bytes': vm_overhead,
        'vm_disk_overhead_human': format_size(vm_overhead),
        'total_reclaimable_bytes': docker['total_reclaimable'],
        'total_reclaimable_human': format_size(docker['total_reclaimable']),
        'objects': {
            'images': docker['images'],
            'containers': docker['containers'],
            'volumes': docker['volumes'],
            'build_cache': docker['build_cache'],
        },
        'volume_details': [
            {
                'name': v['name'],
                'project': v['project'],
                'size_bytes': v['size'],
                'size_human': v['size_human'],
                'in_use': v['in_use'],
            }
            for v in volumes
        ] if volumes else [],
    }
    print(json_module.dumps(summary, indent=2))


def print_header(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


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
                        info = CLEANUP_INFO[cleanup_key].copy()
                        info['size'] = size
                        info['size_human'] = format_size(size)
                        info['path'] = str(path)
                        info['category'] = description
                        # Avoid duplicates (e.g., docker appears twice)
                        if not any(o.get('name') == info['name'] for o in opportunities):
                            opportunities.append(info)
                    else:
                        # Generic cache entry without specific cleanup info
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
    print("  Scanning system for cleanup opportunities...\n")

    opportunities = collect_cleanup_opportunities()

    if not opportunities:
        print("  No significant cleanup opportunities found.")
        return

    # Sort by priority: SAFE first (risk_score), then by size descending
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

    green = '\033[92m'
    yellow = '\033[93m'
    red = '\033[91m'
    bold = '\033[1m'
    reset = '\033[0m'

    if safe_ops:
        print(f"  {green}{bold}PRIORITY 1: SAFE (no downside){reset}")
        print(f"  {'-'*54}")
        for i, op in enumerate(safe_ops, 1):
            print(f"  {i}. {op['name']} - {bold}{op['size_human']}{reset}")
            print(f"     {op['description']}")
            print(f"     Command: {op['command']}")
            print()

    if moderate_ops:
        print(f"  {yellow}{bold}PRIORITY 2: MODERATE (minor rebuild time){reset}")
        print(f"  {'-'*54}")
        for i, op in enumerate(moderate_ops, len(safe_ops) + 1):
            print(f"  {i}. {op['name']} - {bold}{op['size_human']}{reset}")
            print(f"     {op['description']}")
            print(f"     Side effects: {', '.join(op.get('side_effects', []))}")
            print(f"     Command: {op['command']}")
            print()

    if other_ops:
        print(f"  {red}{bold}PRIORITY 3: REVIEW FIRST{reset}")
        print(f"  {'-'*54}")
        for i, op in enumerate(other_ops, len(safe_ops) + len(moderate_ops) + 1):
            print(f"  {i}. {op['name']} - {bold}{op['size_human']}{reset}")
            print(f"     Path: {op['path']}")
            print()

    # Print quick command summary
    print_header("QUICK ACTIONS")

    if safe_ops:
        print(f"  {green}Run all SAFE cleanups (reclaim {format_size(safe_size)}):{reset}")
        print()
        for op in safe_ops:
            print(f"  {op['command']}")
        print()

    # Output structured data for AI consumption
    print_header("STRUCTURED DATA (for AI processing)")
    import json
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

    for cmd in CLEANUP_COMMANDS:
        risk_color = {
            'SAFE': '\033[92m',      # Green
            'MODERATE': '\033[93m',  # Yellow
            'CAUTION': '\033[91m',   # Red
        }.get(cmd['risk'], '')
        reset = '\033[0m'

        print(f"  {'-'*56}")
        print(f"  {cmd['name']}")
        print(f"  Risk: {risk_color}{cmd['risk']}{reset}")
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

    # Duplicates (optional, can be slow)
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
    print("  Run 'space-hog --cleanup-guide' for detailed cleanup instructions.")
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

    args = parser.parse_args()

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
