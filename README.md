# Space Hog

A CLI tool that finds wasted space on your Mac. Identifies large files, caches, duplicates, and cleanup opportunities.

## Features

- **Trash Analysis** - Check how much space your Trash is using
- **Old Downloads** - Find files in Downloads older than 30 days
- **Cache Detection** - Scan common cache locations (browsers, npm, Xcode, Docker, etc.)
- **Space Hog Directories** - Find `node_modules`, `.git`, `DerivedData`, `venv`, and other common bloat
- **Large File Finder** - Locate files above a threshold size
- **Duplicate Detection** - Find duplicate files wasting space

## Installation

```bash
# Clone the repository
git clone https://github.com/dshanklin-bv/space-hog.git
cd space-hog

# Make executable
chmod +x space_hog.py

# Optional: Install globally
pip install -e .
```

## Usage

```bash
# Scan home directory (default)
./space_hog.py

# Scan a specific directory
./space_hog.py /path/to/scan

# Only show items larger than 50MB
./space_hog.py --min-size 50

# Include duplicate file detection (slower)
./space_hog.py --duplicates

# Only check cache locations
./space_hog.py --caches-only

# Only find large files
./space_hog.py --large-files

# Only find space hog directories
./space_hog.py --hogs-only
```

## What It Detects

### Cache Locations
- `~/Library/Caches` - Application caches
- VS Code, Slack, Discord, Chrome caches
- Xcode DerivedData and Archives
- iOS Simulators
- npm, Yarn, Docker caches

### Space Hog Directories
- `node_modules` - Node.js dependencies
- `.git` - Git repositories
- `venv`, `.venv`, `env` - Python virtual environments
- `__pycache__`, `.pytest_cache` - Python caches
- `target` - Rust/Maven build artifacts
- `build`, `dist` - Build directories
- `DerivedData`, `Pods` - Xcode/iOS artifacts
- `.gradle`, `.cargo`, `.nuget` - Package manager caches

## Quick Cleanup Commands

```bash
# Empty trash
rm -rf ~/.Trash/*

# Clear user caches
rm -rf ~/Library/Caches/*

# Clear npm cache
npm cache clean --force

# Clear Docker
docker system prune -a

# Clear Xcode derived data
rm -rf ~/Library/Developer/Xcode/DerivedData/*
```

## Requirements

- Python 3.10+
- macOS (designed for Mac-specific paths)

## License

MIT
