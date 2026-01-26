# Space Hog - AI Agent Instructions

You are helping the user clean up disk space on their Mac. This tool is designed for you.

## Workflow

1. **First run**: `space-hog --help` to understand available commands
2. **Get recommendations**: `space-hog --advise` for prioritized cleanup opportunities
3. **Show user the findings**: Present what can be cleaned and how much space
4. **Ask permission**: ALWAYS get user approval before running ANY cleanup command
5. **Execute with permission**: Only run commands after user says "yes"
6. **Track progress**: `space-hog --stats` shows cumulative savings

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

**ALWAYS ask for user permission before running any cleanup command.**

| Risk Level | Action |
|------------|--------|
| `SAFE` (1) | Low risk, but still ask user before running |
| `MODERATE` (2) | Explain side effects, get confirmation |
| `CAUTION` (3) | Show full details, get explicit approval |

Never run cleanup commands automatically. Always show the user:
1. What will be deleted
2. How much space will be freed
3. Any side effects
4. The exact command

Then wait for explicit "yes" or approval.

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
