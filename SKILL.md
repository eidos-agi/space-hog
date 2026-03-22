# space-hog

Find and reclaim wasted disk space on macOS. Agent-native, zero dependencies.

## Quick Use

```python
from space_hog import collect_cleanup_opportunities
opps = collect_cleanup_opportunities()
for o in opps:
    if o["risk_score"] == 1:  # safe
        print(f"{o['name']}: {o['size_bytes']} bytes → {o['command']}")
```

Or via CLI:

```bash
space-hog --advise    # JSON recommendations with risk scores
space-hog --stats     # Cumulative savings history
```

## Commands

| Command | What It Returns |
|---------|----------------|
| `space-hog --advise` | Prioritized cleanup opportunities with risk scores |
| `space-hog --docker` | Docker VM disk, volumes, sparse file analysis |
| `space-hog --apps` | Unused applications (90+ days) |
| `space-hog --smart` | DMGs, old downloads, Time Machine snapshots |
| `space-hog --stats` | Cleanup history and total space saved |
| `space-hog --caches-only` | Cache locations only |

## Safety Model

Every recommendation has a `risk_score`:
- **1 (SAFE)**: Data regenerates automatically (caches, build artifacts)
- **2 (MODERATE)**: Side effects exist but reversible
- **3 (CAUTION)**: Data loss possible, requires explicit approval

## Invariants

- **Never auto-deletes** — always requires user permission
- `safe_cleanup()` moves to Trash (recoverable) instead of permanent delete
- `--dry-run` previews without acting
- Zero runtime dependencies — stdlib Python only
