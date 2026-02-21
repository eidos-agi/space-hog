"""Docker disk analysis for Space Hog."""

import json
import logging
import re
import shlex
import subprocess
from pathlib import Path

from .utils import format_size, Colors


def _sanitize_label_text(text: str | None) -> str | None:
    """Allow only safe label characters for output and shell use."""
    if not text:
        return None
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '', text).strip()
    return cleaned or None


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
                data = json.loads(line)
                type_name = data.get('Type', '').lower()

                size = _parse_size(data.get('Size', '0B'))
                reclaimable_str = data.get('Reclaimable', '0B')
                # Handle format like "312.7MB (100%)"
                if '(' in reclaimable_str:
                    reclaimable_str = reclaimable_str.split('(')[0].strip()
                reclaimable = _parse_size(reclaimable_str)

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
            except json.JSONDecodeError:
                continue

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logging.warning(f"Failed to inspect Docker disk usage: {e}")

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


def _parse_size(size_str: str) -> int:
    """Parse size strings like '1.592GB', '40.96kB', or '-4.826e+08B'."""
    if not size_str or size_str == '0B':
        return 0
    size_str = size_str.strip()

    # Handle scientific notation like "-4.826e+08B"
    if 'e' in size_str.lower():
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


def analyze_docker_volumes() -> list[dict]:
    """Get detailed volume information including project associations."""
    volumes = []

    try:
        df_output = subprocess.run(
            ['docker', 'system', 'df', '-v', '--format', '{{json .}}'],
            capture_output=True, text=True, check=True, timeout=30
        )

        data = json.loads(df_output.stdout)
        volume_list = data.get('Volumes', [])

        for vol in volume_list:
            labels = vol.get('Labels', '')
            # Parse project from labels
            project = None
            if 'com.supabase.cli.project=' in labels:
                for part in labels.split(','):
                    if 'com.supabase.cli.project=' in part:
                        project = part.split('=', 1)[1]
                        break
            elif 'com.docker.compose.project=' in labels:
                for part in labels.split(','):
                    if 'com.docker.compose.project=' in part:
                        project = part.split('=', 1)[1]
                        break
            project = _sanitize_label_text(project)

            # Parse size
            size_str = vol.get('Size', '0B')
            size = _parse_size(size_str)
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

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        logging.warning(f"Failed to inspect Docker volumes: {e}")

    return sorted(volumes, key=lambda x: -x['size'])


def print_docker_analysis():
    """Print detailed Docker disk analysis."""
    from .utils import print_header

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

    c = Colors

    # VM Disk analysis
    if docker['vm_disk_allocated'] > 0:
        vm_logical = docker.get('vm_disk_logical', docker['vm_disk_allocated'])
        vm_actual = docker['vm_disk_allocated']
        vm_objects = docker['vm_disk_used']
        vm_overhead = vm_actual - vm_objects if vm_actual > vm_objects else 0

        print(f"  {c.BOLD}VM DISK (Docker.raw){c.RESET}")
        print(f"  {'-'*50}")
        print(f"  Max size (logical):     {format_size(vm_logical)}")
        print(f"  Actual disk usage:      {format_size(vm_actual)}")
        print(f"  Docker objects inside:  {format_size(vm_objects)}")

        if vm_overhead > 1024 * 1024 * 1024:  # > 1GB overhead
            overhead_pct = (vm_overhead / vm_actual) * 100 if vm_actual > 0 else 0
            print(f"  {c.YELLOW}VM overhead/deleted:     {format_size(vm_overhead)} ({overhead_pct:.0f}% of disk){c.RESET}")
            print()
            print(f"  {c.YELLOW}The {format_size(vm_overhead)} gap is from deleted images/containers")
            print(f"  that were removed inside Docker but the disk file never shrinks.{c.RESET}")
        print()

    # Docker objects breakdown
    print(f"  {c.BOLD}DOCKER OBJECTS{c.RESET}")
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
    print(f"  {c.BOLD}RECOMMENDATIONS{c.RESET}")
    print(f"  {'-'*50}")

    if docker['total_reclaimable'] > 100 * 1024 * 1024:
        print(f"  {c.GREEN}1. Prune unused objects:{c.RESET}")
        print(f"     docker system prune -a")
        print(f"     (Reclaims ~{format_size(docker['total_reclaimable'])})")
        print()

    if docker['volumes']['reclaimable'] > 50 * 1024 * 1024:
        print(f"  {c.YELLOW}2. Remove unused volumes (check first!):{c.RESET}")
        print(f"     docker volume prune")
        print(f"     (Reclaims ~{format_size(docker['volumes']['reclaimable'])})")
        print()

    vm_overhead = docker['vm_disk_allocated'] - docker['vm_disk_used']
    if vm_overhead > 5 * 1024 * 1024 * 1024:
        print(f"  {c.RED}3. Reclaim VM overhead ({format_size(vm_overhead)}):{c.RESET}")
        print(f"     Option A: Docker Desktop → Settings → Resources")
        print(f"               → Reduce 'Virtual disk limit'")
        print(f"     Option B: Factory reset Docker Desktop")
        print(f"     Option C: Stop Docker, delete Docker.raw, restart")
        print()

    # Volume details
    volumes = analyze_docker_volumes()
    if volumes:
        print(f"  {c.BOLD}VOLUMES BY PROJECT{c.RESET}")
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

        for proj, data in sorted(projects.items(), key=lambda x: -x[1]['total_size']):
            in_use_marker = ''
            vol_count = len(data['volumes'])
            orphan_count = sum(1 for v in data['volumes'] if v['links'] == 0)
            if orphan_count == vol_count:
                in_use_marker = f' {c.YELLOW}(orphaned){c.RESET}'
            elif orphan_count > 0:
                in_use_marker = f' {c.YELLOW}({orphan_count} orphaned){c.RESET}'

            print(f"  {proj:<25} {format_size(data['total_size']):>10} ({vol_count} volumes){in_use_marker}")

        print()
        if orphaned:
            orphan_size = sum(v['size'] for v in orphaned)
            print(f"  {c.YELLOW}Orphaned volumes (no running containers): {format_size(orphan_size)}{c.RESET}")
            print(f"  To remove orphaned volumes for a project:")
            orphan_projects = sorted({v.get('project') for v in orphaned if v.get('project')})
            for proj in orphan_projects:
                quoted_project = shlex.quote(proj)
                print(f"    docker volume rm $(docker volume ls -q -f label=com.docker.compose.project={quoted_project})")
            print()

    # JSON output for AI
    print()
    print(f"  {c.BOLD}STRUCTURED DATA{c.RESET}")
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
    print(json.dumps(summary, indent=2))
