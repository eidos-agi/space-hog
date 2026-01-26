"""Space Hog - Find wasted space on your Mac."""

from .utils import format_size, get_dir_size, FileInfo
from .scanners import find_large_files, find_space_hogs, find_duplicates
from .caches import check_caches, get_trash_size, get_downloads_analysis
from .docker import analyze_docker, analyze_docker_volumes
from .applications import scan_applications, get_app_info
from .advisor import collect_cleanup_opportunities
from .stats import record_cleanup, run_cleanup, get_summary, print_stats
from .smart import (
    find_dmg_files,
    find_old_downloads,
    find_localization_files,
    find_time_machine_snapshots,
    get_smart_recommendations,
)
from .safe_delete import (
    move_to_trash,
    trash_contents,
    safe_cleanup,
)
from .cli import main

__version__ = '0.4.0'
__all__ = [
    'format_size',
    'get_dir_size',
    'FileInfo',
    'find_large_files',
    'find_space_hogs',
    'find_duplicates',
    'check_caches',
    'get_trash_size',
    'get_downloads_analysis',
    'analyze_docker',
    'analyze_docker_volumes',
    'scan_applications',
    'get_app_info',
    'collect_cleanup_opportunities',
    'record_cleanup',
    'run_cleanup',
    'get_summary',
    'print_stats',
    'find_dmg_files',
    'find_old_downloads',
    'find_localization_files',
    'find_time_machine_snapshots',
    'get_smart_recommendations',
    'move_to_trash',
    'trash_contents',
    'safe_cleanup',
    'main',
]
