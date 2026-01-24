---
name: space-hog
description: Disk space analysis and cleanup advisor for macOS
triggers:
  - disk space
  - clean up
  - docker bloat
  - npm cache
  - what's using space
  - storage
  - free up space
---

# Space Hog - Disk Space Advisor

Analyze and reclaim wasted disk space on macOS.

## Quick Start

```bash
cd ~/repos-personal/space-hog

# Prioritized recommendations (start here)
python3 space_hog.py --advise

# Docker deep-dive (VM bloat, volumes by project)
python3 space_hog.py --docker

# Full scan
python3 space_hog.py
```

## Cleanup Priority Order

Always clean in this order (safest → riskier):

### Priority 1: SAFE (no downside, do these first)

| Command | What it clears |
|---------|---------------|
| `npm cache clean --force` | NPM package cache |
| `rm -rf ~/Library/Caches/*` | App caches |
| `rm -rf ~/.cache/*` | CLI tool caches |
| `xcrun simctl delete unavailable` | Old iOS Simulators |
| `rm -rf ~/.Trash/*` | Trash |

### Priority 2: MODERATE (requires rebuild)

| Command | What it clears | Side effect |
|---------|---------------|-------------|
| `docker system prune -a` | Unused images | Must re-pull images |
| `docker volume prune` | Unused volumes | Check projects first! |

### Priority 3: Docker VM Bloat

Docker.raw doesn't auto-shrink. To reclaim:
1. Docker Desktop → Settings → Resources → Reduce "Virtual disk limit"
2. Or: Factory reset Docker Desktop
3. Or: Stop Docker, delete `~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw`, restart

## Docker Volume Safety

ALWAYS check what's using volumes before deleting:

```bash
# See volumes grouped by project
python3 space_hog.py --docker

# Remove volumes for a specific orphaned project
docker volume rm $(docker volume ls -q -f 'label=com.docker.compose.project=PROJECT_NAME')
```

## Workflow

1. Run `python3 space_hog.py --advise` for prioritized recommendations
2. Execute SAFE cleanups (user approval for each)
3. If Docker is large, run `--docker` to see volume breakdown
4. Check volume projects before deleting any
5. Log cleanup results to CHANGELOG.md

## Interpreting Output

Both `--advise` and `--docker` output structured JSON at the end. Parse this for:
- `total_reclaimable_bytes` - Total space that can be freed
- `safe_reclaimable_bytes` - Space from SAFE operations only
- `vm_disk_bloat_bytes` - Docker VM overhead
- `volume_details` - Per-volume project associations

## Safety Rules

1. Never delete Docker volumes without showing user which projects they belong to
2. Always confirm before running MODERATE or higher risk commands
3. Document what was cleaned in CHANGELOG.md
4. If Docker VM bloat is large, explain the manual reclaim options
