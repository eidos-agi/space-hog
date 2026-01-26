# Space Hog

A CLI tool that finds wasted space on your Mac. Identifies large files, caches, duplicates, unused applications, and Docker bloat.

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
git clone https://github.com/dshanklin-bv/space-hog.git
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
