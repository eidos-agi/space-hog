![Space Hog](logo.png)

# Space Hog

A CLI tool that finds and reclaims wasted disk space on macOS.

### Built for AI Agents

Space Hog is designed to be run by AI coding assistants like [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex CLI](https://github.com/openai/codex), and [Gemini CLI](https://github.com/google-gemini/gemini-cli).

Why? Disk cleanup is tedious for humans but trivial for AI:
- **Structured output** — JSON data the AI can parse and reason about
- **Safety ratings** — AI knows which commands are safe to run without asking
- **Context awareness** — AI understands your Docker projects, dev environments, and what's actually in use
- **Automatic execution** — AI runs the cleanup commands and tracks cumulative savings

Just ask your AI assistant to "clean up my disk" and let it handle the rest.

## AI Agent Workflow

**If you're an AI agent, follow this workflow:**

```bash
# 1. First, understand what's available
space-hog --help

# 2. Get prioritized recommendations with safety ratings
space-hog --advise

# 3. Show user the recommendations and ASK PERMISSION before any cleanup
#    - SAFE (risk_score: 1): Low risk, explain briefly
#    - MODERATE (risk_score: 2): Explain side effects
#    - CAUTION (risk_score: 3): Show full details, get explicit approval

# 4. Only run cleanup commands after user says "yes"

# 5. Track your progress
space-hog --stats
```

**Key flags for AI agents:**
- `--advise` — Returns JSON with `risk_score` (1=safe, 2=moderate, 3=caution)
- `--stats` — Shows cumulative space saved across sessions
- `--smart` — Finds DMGs, old downloads, Time Machine snapshots

**Safety rules:**
- **ALWAYS ask user permission before running any cleanup command**
- Show what will be deleted, space to be freed, and side effects
- Wait for explicit "yes" before executing
- Use the exact command from the output (handles escaping)
- The `run_cleanup()` function measures before/after to verify actual savings

## Features

- **Prioritized Cleanup Advice** - AI-friendly recommendations sorted by safety
- **Docker Deep-Dive** - VM disk bloat analysis, sparse file detection, volume tracking
- **Application Analysis** - Find unused apps and AI-replaceable tools
- **Cache Detection** - Scan npm, Xcode, browsers, Docker, and more
- **Space Hog Directories** - Find `node_modules`, `.git`, `DerivedData`, `venv`
- **Large File & Duplicate Detection** - Locate files wasting space

## Installation

```bash
# Clone the repository
git clone https://github.com/rhea-impact/space-hog.git
cd space-hog

# Install (editable mode for development)
pip install -e .

# Or run directly
python3 space_hog.py --help
```

## Quick Start

```bash
# Get prioritized cleanup recommendations
space-hog --advise

# Analyze Docker disk usage (VM bloat, volumes)
space-hog --docker

# Find unused/AI-replaceable applications
space-hog --apps

# Full system scan
space-hog
```

## Commands

| Command | Description |
|---------|-------------|
| `space-hog --advise` | Prioritized cleanup recommendations (SAFE → MODERATE) |
| `space-hog --docker` | Docker deep-dive: VM disk, sparse files, volumes by project |
| `space-hog --apps` | Find apps unused in 90+ days, AI-replaceable suggestions |
| `space-hog --stats` | Show cleanup history and total space saved |
| `space-hog --cleanup-guide` | Detailed guide with safety info for each cleanup |
| `space-hog` | Full scan: trash, downloads, caches, large files |
| `space-hog --caches-only` | Only check cache locations |
| `space-hog --duplicates` | Include duplicate file detection (slower) |

### Options

```bash
--min-size 50      # Only show items > 50MB (default: 100)
--days-unused 180  # Apps unused threshold (default: 90)
--duplicates       # Scan for duplicate files
```

## What It Detects

### Cache Locations
- `~/Library/Caches` - Application caches
- `~/.npm`, `~/.yarn/cache` - Package manager caches
- VS Code, Slack, Discord, Chrome caches
- Xcode DerivedData, Archives, iOS Simulators
- Docker Desktop VM disk

### Space Hog Directories
- `node_modules` - Node.js dependencies
- `.git` - Git repositories (flags bloated ones)
- `venv`, `.venv` - Python virtual environments
- `DerivedData`, `Pods` - Xcode/iOS artifacts
- `target`, `build`, `dist` - Build artifacts

### Docker Analysis
- **VM disk bloat** - Detects sparse file overhead from deleted images
- **Volume tracking** - Groups volumes by project, identifies orphans
- **Explains why** `docker system prune` doesn't free macOS disk space

### Application Analysis
- Apps not opened in 90+ days
- AI-replaceable apps (translation, writing tools, etc.)
- Size breakdown of /Applications

## Safe Cleanup Commands

These commands are safe to run (data regenerates automatically):

```bash
npm cache clean --force          # NPM cache
rm -rf ~/Library/Caches/*        # App caches
rm -rf ~/.cache/*                # CLI tool caches
xcrun simctl delete unavailable  # Old iOS Simulators
```

Use `space-hog --cleanup-guide` for detailed safety information on each command.

## Package Structure

```
space_hog/
├── cli.py           # Entry point
├── advisor.py       # Prioritized recommendations
├── docker.py        # Docker/VM disk analysis
├── applications.py  # Unused app detection
├── stats.py         # Cleanup history tracking
├── scanners.py      # File system scanning
├── caches.py        # Cache location checks
├── constants.py     # Patterns and cleanup info
└── utils.py         # Shared utilities
```

## Requirements

- Python 3.10+
- macOS (designed for Mac-specific paths)
- Docker Desktop (optional, for `--docker`)

## License

MIT

## Fork Workflow

This repo is a fork of [rhea-impact/space-hog](https://github.com/rhea-impact/space-hog).

**Remotes:**
```
origin   → dshanklin-bv/space-hog (this fork)
upstream → rhea-impact/space-hog (public source)
```

**Sync from upstream:**
```bash
git fetch upstream
git merge upstream/main
git push origin main
```

**Push fixes to upstream:**
```bash
# Create a branch for your fix
git checkout -b fix/my-fix

# Make changes, commit
git add -A && git commit -m "Fix: description"

# Push to your fork
git push origin fix/my-fix

# Create PR on GitHub: dshanklin-bv/space-hog → rhea-impact/space-hog
gh pr create --repo rhea-impact/space-hog --head dshanklin-bv:fix/my-fix
```
