# Space Hog - AI Agent Instructions

You are helping the user clean up disk space on their Mac. This tool is designed for you.

## Workflow

1. **First run**: `space-hog --help` to understand available commands
2. **Get recommendations**: `space-hog --advise` for prioritized cleanup opportunities
3. **Execute safe cleanups**: Run commands marked `risk: SAFE` without asking
4. **Ask for moderate**: Commands marked `risk: MODERATE` need user confirmation
5. **Track progress**: `space-hog --stats` shows cumulative savings

## Understanding the Output

The `--advise` command outputs JSON with:
```json
{
  "opportunities": [
    {
      "name": "Clear NPM Cache",
      "size_bytes": 3200000000,
      "risk": "SAFE",           // SAFE, MODERATE, or CAUTION
      "risk_score": 1,          // 1=safe, 2=moderate, 3=caution
      "command": "npm cache clean --force",
      "side_effects": ["Next npm install will re-download"]
    }
  ]
}
```

## Safety Rules

| Risk Level | Action |
|------------|--------|
| `SAFE` (1) | Run automatically, no confirmation needed |
| `MODERATE` (2) | Explain side effects, ask user before running |
| `CAUTION` (3) | Show full details, get explicit approval |

## Running Cleanups

Use the exact commands from the output. They handle path escaping correctly.

For verified cleanup tracking, use the Python API:
```python
from space_hog import run_cleanup
result = run_cleanup("rm -rf ~/.npm/_npx/*", "NPM npx cache", "npm")
# Returns: {'success': True, 'bytes_freed': 3200000000, 'recorded': True}
```

## Common Commands

```bash
space-hog --advise      # Prioritized recommendations (start here)
space-hog --smart       # Find DMGs, old downloads, TM snapshots
space-hog --docker      # Docker-specific analysis
space-hog --apps        # Unused applications
space-hog --stats       # Show cleanup history
```

## What Gets Detected

- **AI tools**: Ollama models (often 50-100GB), Codeium, Gemini, Claude caches
- **Dev caches**: npm, yarn, pnpm, cargo, gradle, maven, cocoapods
- **Xcode**: DerivedData, device symbols, simulators, archives
- **Docker**: Images, volumes, VM disk bloat
- **iOS backups**: Can be 20-100GB each
- **Mail/Downloads**: Old files, DMG installers
