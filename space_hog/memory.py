"""Memory and process analysis for Space Hog.

Tracks RAM consumers, autostart items, and background processes.
"""

import subprocess
from pathlib import Path
from typing import Optional

from .utils import format_size, print_header, Colors


def get_top_ram_consumers(limit: int = 15) -> list[dict]:
    """Get top RAM-consuming processes.

    Returns list of dicts with process info.
    """
    try:
        # Get process list sorted by memory
        result = subprocess.run(
            ['ps', 'aux', '-m'],
            capture_output=True, text=True, timeout=10
        )

        processes = []
        for line in result.stdout.strip().split('\n')[1:limit+1]:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                rss_kb = int(parts[5])  # RSS in KB
                command = parts[10]

                # Extract app name from path
                app_name = command.split('/')[-1].split()[0]
                if '.app' in command:
                    # Extract app bundle name
                    for part in command.split('/'):
                        if '.app' in part:
                            app_name = part.replace('.app', '')
                            break

                processes.append({
                    'pid': parts[1],
                    'user': parts[0],
                    'cpu': float(parts[2]),
                    'mem_percent': float(parts[3]),
                    'rss_bytes': rss_kb * 1024,
                    'rss_human': format_size(rss_kb * 1024),
                    'command': command,
                    'app_name': app_name,
                })

        return processes

    except (subprocess.TimeoutExpired, Exception) as e:
        return []


def get_login_items() -> list[str]:
    """Get apps that start at login."""
    try:
        result = subprocess.run(
            ['osascript', '-e',
             'tell application "System Events" to get the name of every login item'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return [item.strip() for item in result.stdout.strip().split(',')]
    except (subprocess.TimeoutExpired, Exception):
        pass
    return []


def get_launch_agents() -> list[dict]:
    """Get user LaunchAgents (background services)."""
    agents = []
    launch_agents_dir = Path.home() / 'Library' / 'LaunchAgents'

    if launch_agents_dir.exists():
        for plist in launch_agents_dir.glob('*.plist'):
            # Check if loaded
            label = plist.stem
            try:
                result = subprocess.run(
                    ['launchctl', 'list', label],
                    capture_output=True, text=True, timeout=5
                )
                is_running = result.returncode == 0
            except:
                is_running = False

            agents.append({
                'name': label,
                'path': str(plist),
                'running': is_running,
            })

    return agents


def get_launch_daemons() -> list[dict]:
    """Get system LaunchDaemons the user might control."""
    daemons = []

    # Check user-installed daemons (via Homebrew, etc.)
    homebrew_daemons = []
    launch_agents_dir = Path.home() / 'Library' / 'LaunchAgents'

    if launch_agents_dir.exists():
        for plist in launch_agents_dir.glob('homebrew.*.plist'):
            label = plist.stem
            try:
                result = subprocess.run(
                    ['launchctl', 'list', label],
                    capture_output=True, text=True, timeout=5
                )
                is_running = result.returncode == 0
            except:
                is_running = False

            daemons.append({
                'name': label.replace('homebrew.mxcl.', ''),
                'label': label,
                'path': str(plist),
                'running': is_running,
                'type': 'homebrew',
            })

    return daemons


def aggregate_by_app(processes: list[dict]) -> list[dict]:
    """Aggregate RAM usage by app (combining helper processes)."""
    by_app = {}

    for proc in processes:
        app = proc['app_name']
        if app not in by_app:
            by_app[app] = {
                'app_name': app,
                'rss_bytes': 0,
                'process_count': 0,
                'pids': [],
            }
        by_app[app]['rss_bytes'] += proc['rss_bytes']
        by_app[app]['process_count'] += 1
        by_app[app]['pids'].append(proc['pid'])

    # Convert to list and add human-readable size
    result = list(by_app.values())
    for item in result:
        item['rss_human'] = format_size(item['rss_bytes'])

    # Sort by RAM usage
    result.sort(key=lambda x: -x['rss_bytes'])

    return result


def print_memory_analysis():
    """Print memory and process analysis."""
    c = Colors

    print_header("MEMORY & PROCESS ANALYSIS")

    # Get data
    processes = get_top_ram_consumers(limit=30)
    aggregated = aggregate_by_app(processes)
    login_items = get_login_items()
    launch_agents = get_launch_agents()

    # Top RAM consumers (aggregated by app)
    print(f"  {c.BOLD}TOP RAM CONSUMERS{c.RESET}")
    print(f"  {'-'*50}")

    total_shown = 0
    for app in aggregated[:10]:
        procs = f" ({app['process_count']} processes)" if app['process_count'] > 1 else ""
        print(f"  {app['rss_human']:>10}  {app['app_name']}{procs}")
        total_shown += app['rss_bytes']

    print(f"  {'-'*50}")
    print(f"  {'Total:':>10}  {format_size(total_shown)}")
    print()

    # Login items
    if login_items:
        print(f"  {c.BOLD}LOGIN ITEMS (start at login){c.RESET}")
        print(f"  {'-'*50}")
        for item in login_items:
            # Check if it's in top RAM consumers
            ram_info = ""
            for app in aggregated:
                if app['app_name'].lower() in item.lower() or item.lower() in app['app_name'].lower():
                    ram_info = f" - {c.YELLOW}{app['rss_human']} RAM{c.RESET}"
                    break
            print(f"    {item}{ram_info}")
        print()
        print(f"  {c.YELLOW}To remove: System Settings > General > Login Items{c.RESET}")
        print()

    # LaunchAgents
    running_agents = [a for a in launch_agents if a['running']]
    if running_agents:
        print(f"  {c.BOLD}RUNNING LAUNCH AGENTS{c.RESET}")
        print(f"  {'-'*50}")
        for agent in running_agents:
            name = agent['name']
            # Shorten long names
            if len(name) > 40:
                name = name[:37] + "..."
            print(f"    {name}")
        print()
        print(f"  {c.YELLOW}To stop: launchctl unload ~/Library/LaunchAgents/<name>.plist{c.RESET}")
        print()

    # Suggestions
    print(f"  {c.BOLD}SUGGESTIONS{c.RESET}")
    print(f"  {'-'*50}")

    # Check preferences
    from .preferences import is_essential

    suggestions = []

    # Check for known heavy apps (skip essential ones)
    for app in aggregated[:5]:
        if app['rss_bytes'] > 1024 * 1024 * 1024:  # > 1GB
            if is_essential(app['app_name']):
                suggestions.append(f"  {c.GREEN}•{c.RESET} {app['app_name']} using {app['rss_human']} (marked essential)")
            else:
                suggestions.append(f"  {c.YELLOW}•{c.RESET} {app['app_name']} using {app['rss_human']} - consider closing when not needed")

    # Check for apps in both login items and RAM (skip essential ones)
    for item in login_items:
        if is_essential(item):
            continue
        for app in aggregated:
            if app['app_name'].lower() in item.lower():
                if app['rss_bytes'] > 200 * 1024 * 1024:  # > 200MB
                    suggestions.append(f"  {c.YELLOW}•{c.RESET} {item} auto-starts and uses {app['rss_human']} - disable if not essential")
                break

    if suggestions:
        for s in suggestions[:5]:
            print(s)
    else:
        print(f"  {c.GREEN}No major memory concerns detected.{c.RESET}")

    print()

    # Structured output
    print_header("STRUCTURED DATA (for AI processing)")
    import json
    summary = {
        'top_consumers': [
            {
                'app': a['app_name'],
                'ram_bytes': a['rss_bytes'],
                'ram_human': a['rss_human'],
                'process_count': a['process_count'],
            }
            for a in aggregated[:10]
        ],
        'login_items': login_items,
        'running_agents': [a['name'] for a in running_agents],
        'total_ram_top10': sum(a['rss_bytes'] for a in aggregated[:10]),
    }
    print(json.dumps(summary, indent=2))


def stop_launch_agent(label: str) -> dict:
    """Stop a LaunchAgent.

    Returns dict with success status.
    """
    plist_path = Path.home() / 'Library' / 'LaunchAgents' / f'{label}.plist'

    if not plist_path.exists():
        return {'success': False, 'error': f'LaunchAgent not found: {label}'}

    try:
        result = subprocess.run(
            ['launchctl', 'unload', str(plist_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return {'success': True, 'message': f'Stopped {label}'}
        else:
            return {'success': False, 'error': result.stderr}
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def remove_login_item(app_name: str) -> dict:
    """Remove an app from login items.

    Returns dict with success status.
    """
    try:
        result = subprocess.run(
            ['osascript', '-e',
             f'tell application "System Events" to delete login item "{app_name}"'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return {'success': True, 'message': f'Removed {app_name} from login items'}
        else:
            return {'success': False, 'error': result.stderr}
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
