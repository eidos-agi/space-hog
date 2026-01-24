---
name: space-hog
description: Disk space analysis and cleanup advisor for macOS
triggers:
  - disk space
  - clean up
  - docker bloat
  - docker space
  - npm cache
  - what's using space
  - storage
  - free up space
---

# Space Hog - Disk Space Advisor

Analyze and reclaim wasted disk space on macOS.

## Commands

```bash
cd ~/repos-personal/space-hog

python3 space_hog.py --advise   # Prioritized recommendations
python3 space_hog.py --docker   # Docker deep-dive
python3 space_hog.py            # Full scan
```

## Cleanup Priority Order

### Priority 1: SAFE (no downside)
```bash
npm cache clean --force          # NPM cache
rm -rf ~/Library/Caches/*        # App caches
rm -rf ~/.cache/*                # CLI tool caches
xcrun simctl delete unavailable  # iOS Simulators
rm -rf ~/.Trash/*                # Trash
```

### Priority 2: MODERATE (rebuild time)
```bash
docker system prune -a           # Unused images (doesn't shrink VM disk!)
docker volume prune              # Unused volumes (check projects first!)
```

---

# Docker Disk Analysis

## Understanding Docker.raw

Docker Desktop uses a virtual disk file at:
```
~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
```

**Critical insight:** This is a **sparse file** with THREE different sizes:

| Metric | What it means |
|--------|---------------|
| **Logical size** (`ls -lah`) | Max allocation limit (e.g., 60 GB) |
| **Actual disk usage** (`du -h`) | Real bytes on your disk (e.g., 28 GB) |
| **Docker objects** (`docker system df`) | Images + containers + volumes (e.g., 2 GB) |

The gap between "actual disk usage" and "Docker objects" is **overhead from deleted images/containers**. Docker removed them inside the VM, but the VM disk file NEVER shrinks automatically.

## Why `docker system prune` Doesn't Free Host Disk Space

When you run `docker system prune -a`:
1. Docker deletes images/containers inside the VM
2. The VM's filesystem marks those blocks as free
3. But the Docker.raw file on macOS **doesn't shrink**
4. The space is "freed" inside Docker but still allocated on your Mac

This is why you can have 28 GB actual disk usage but only 2 GB of Docker objects.

## How to Actually Reclaim VM Overhead

The ONLY ways to shrink Docker.raw:

**Option A: Reduce disk limit (preferred)**
1. Docker Desktop → Settings → Resources
2. Reduce "Virtual disk limit" (e.g., to 16 GB)
3. Click Apply & Restart
4. Docker will shrink the file to fit

**Option B: Factory reset**
1. Docker Desktop → Troubleshoot → Reset to factory defaults
2. Loses all images, containers, volumes
3. Recreates a fresh small Docker.raw

**Option C: Manual delete**
```bash
# Stop Docker Desktop first!
rm ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
# Restart Docker Desktop - it recreates at minimal size
```

## Volume Analysis

Run `python3 space_hog.py --docker` to see volumes grouped by project:

```
VOLUMES BY PROJECT
--------------------------------------------------
whospent                    266.8 MB (5 volumes) (orphaned)
Sable                        45.0 MB (1 volumes) (orphaned)
zen-mcp-server               10.7 KB (1 volumes) (orphaned)
```

**Orphaned** = no running containers using these volumes.

### Cleaning Up Orphaned Project Volumes

```bash
# Remove all volumes for a specific project
docker volume rm $(docker volume ls -q -f 'label=com.docker.compose.project=PROJECT_NAME')

# Example: clean up old Supabase project
docker volume rm $(docker volume ls -q -f 'label=com.docker.compose.project=Sable')
```

### Volume Safety Rules

1. **Always run `--docker` first** to see which projects own which volumes
2. **Check if containers are running** for that project before deleting
3. **Database volumes contain data** - deleting loses all DB data for that project
4. Supabase volumes typically include: `db`, `storage`, `edge_runtime`, `config`

## Interpreting JSON Output

Both `--advise` and `--docker` output structured JSON:

```json
{
  "vm_disk_logical_bytes": 64000000000,    // Max allocation (what ls shows)
  "vm_disk_actual_bytes": 28000000000,     // Real disk usage (what du shows)
  "vm_disk_objects_bytes": 2000000000,     // Docker images/containers/volumes
  "vm_disk_overhead_bytes": 26000000000,   // Deleted stuff (actual - objects)
  "volume_details": [
    {"name": "supabase_db_whospent", "project": "whospent", "size_bytes": 266000000, "in_use": false}
  ]
}
```

## Decision Tree

```
Is Docker using lots of space?
├── Run: python3 space_hog.py --docker
├── Check "Actual disk usage" vs "Docker objects"
│   ├── Big gap? → VM overhead from deleted images
│   │   └── Reduce disk limit in Docker Desktop settings
│   └── Small gap? → Active images are the issue
│       └── docker system prune -a
├── Check volumes by project
│   ├── Orphaned volumes? → Safe to delete if project unused
│   └── Active volumes? → Don't delete without user confirmation
```

## Workflow

1. `python3 space_hog.py --advise` - get prioritized recommendations
2. Run SAFE cleanups (always safe, no confirmation needed)
3. If Docker is large, run `--docker` to understand why
4. Explain the logical/actual/objects breakdown to user
5. For VM overhead: recommend reducing disk limit in settings
6. For volumes: show projects, confirm before deleting
7. Log results to CHANGELOG.md
