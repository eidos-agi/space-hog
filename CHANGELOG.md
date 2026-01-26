# Changelog

## 2026-01-25

### Docker Volume Cleanup

Investigated and cleaned orphaned Docker volumes.

**Volumes traced to source:**
| Volume | Source Project | Location |
|--------|---------------|----------|
| whospent | WhoSpent app | `~/repos-bv/bcm-capital/whospent/` |
| Sable | Sable app | `~/repos-aic/Sable/` |
| aicdashboard | AIC Dashboard | `~/repos-aic/aic/supabase/` |
| hrezmztjmvzzibfhvpyo | Supabase cloud project | Linked by multiple apps |
| zen-mcp-server | Zen MCP | `~/repos/zen-mcp-server/` |

**Deleted (unused):**
- supabase_db_whospent (266 MB)
- supabase_edge_runtime_whospent
- supabase_config_whospent
- supabase_inbucket_whospent
- supabase_storage_whospent
- supabase_edge_runtime_Sable (45 MB)
- supabase_edge_runtime_aicdashboard
- supabase_edge_runtime_hrezmztjmvzzibfhvpyo

**Kept:** zen-mcp-server (11 KB)

**Result:** 9 volumes → 1 volume, freed 312 MB inside Docker

**Key learning:** Deleting volumes doesn't shrink Docker.raw - the VM overhead actually increased slightly (26.0 → 26.6 GB) because the deleted blocks become dead space in the sparse file.

---

## 2026-01-23

### Cleanup Session
Ran full triage on system.

**Before:**
- Total reclaimable: 141 GB

**Actions taken:**
1. `npm cache clean --force` - Freed ~30.6 GB (33.3 GB → 2.7 GB)
2. `rm -rf ~/Library/Caches/*` - Freed ~22.5 GB
3. `rm -rf ~/.cache/*` - Freed ~18 GB
4. `xcrun simctl delete unavailable` - Freed ~2.6 GB (6.3 GB → 3.7 GB)
5. `docker system prune -a` - Freed 1.6 GB

**Total freed: ~75 GB**

### Findings

**Docker VM disk issue:**
- Docker Desktop's VM disk (`Docker.raw`) is 60 GB
- Actual Docker usage: only 1.9 GB
- The VM disk doesn't auto-shrink after pruning

**Fix options for Docker disk bloat:**
1. Docker Desktop → Settings → Resources → reduce disk size limit
2. Factory reset Docker Desktop (nuclear option)
3. Manual: Stop Docker, delete `Docker.raw`, restart (it recreates at smaller size)

### Remaining
- Docker VM overhead: ~58 GB (fixable via settings)
- iOS Simulators: 3.7 GB
- NPM cache: 2.7 GB (rebuilding)
- App caches: ~1.1 GB (Slack, VS Code)
