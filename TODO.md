# Space Hog - TODO

## Developer-focused

- [ ] **Xcode cleanup** - DerivedData, old archives, device support files
  - `~/Library/Developer/Xcode/DerivedData/` (5-50 GB typical)
  - `~/Library/Developer/Xcode/Archives/`
  - `~/Library/Developer/Xcode/iOS DeviceSupport/`

- [ ] **Homebrew** - old formula versions, cache
  - `brew cleanup --dry-run` to preview
  - `$(brew --cache)` location

- [ ] **JetBrains IDEs** - caches, logs, local history
  - `~/Library/Caches/JetBrains/`
  - `~/Library/Application Support/JetBrains/`

- [ ] **Git optimization** - detect bloated `.git` dirs
  - Flag repos with `.git` > 500 MB
  - Suggest `git gc --aggressive`
  - Detect large binaries that should use LFS

## System/App bloat

- [ ] **Time Machine local snapshots**
  - `tmutil listlocalsnapshots /`
  - Can be 50+ GB on laptops

- [ ] **Log files** - system logs, crash reports
  - `~/Library/Logs/`
  - `~/Library/Logs/DiagnosticReports/`
  - `/var/log/` (requires sudo)

- [ ] **Mail attachments**
  - `~/Library/Mail/` grows silently
  - Attachments cached even after deletion

- [ ] **Browser profiles** - caches, old downloads
  - Chrome: `~/Library/Application Support/Google/Chrome/`
  - Safari: `~/Library/Caches/com.apple.Safari/`
  - Firefox: `~/Library/Application Support/Firefox/`

## Media/Communication apps

- [ ] **Slack cache**
  - `~/Library/Application Support/Slack/`
  - Often 5-10 GB of cached files

- [ ] **Spotify/Music offline cache**
  - `~/Library/Application Support/Spotify/`
  - `~/Library/Caches/com.spotify.client/`

- [ ] **Zoom recordings**
  - `~/Documents/Zoom/`
  - Local recordings people forget about

- [ ] **Podcast downloads**
  - Apple Podcasts: `~/Library/Group Containers/*.groups.com.apple.podcasts/`
  - Old episodes accumulate

## Quality of life features

- [ ] **Interactive mode** - guided cleanup wizard
  - Step through each category
  - Preview before delete
  - Confirmation prompts

- [ ] **Watch mode** - monitor disk usage over time
  - Track space by category
  - Alert on thresholds
  - Historical comparison

- [x] **Unused apps** - apps not opened in 6+ months (`--apps`)
  - Check `mdls -name kMDItemLastUsedDate`
  - List with size and last used date
  - AI-replaceable app suggestions

- [ ] **Screenshot cleanup**
  - Desktop screenshots (`Screenshot *.png`)
  - Downloads folder screenshots
  - Age-based suggestions

## Completed

- [x] Basic scanning (trash, downloads, caches, node_modules, .git, venv)
- [x] Docker analysis with sparse file detection
- [x] Volume project tracking
- [x] Prioritized recommendations (`--advise`)
- [x] Cleanup guide (`--cleanup-guide`)
- [x] Applications analysis (`--apps`) - unused apps, AI-replaceable suggestions
- [x] Modular refactor - split into `space_hog/` package with functional modules
