---
id: '0001'
title: 5 macOS signals for detecting unused software — layered confidence model
status: open
evidence: HIGH
sources: 1
created: '2026-03-22'
---

## Claim

No single signal reliably detects unused software. But 5 signals combined create a layered confidence model:

**1. Spotlight kMDItemLastUsedDate (GUI apps)**
`mdls -name kMDItemLastUsedDate /Applications/AppName.app` — date user last opened the app. Only triggered by actual user opens, not automated processes. Null means never opened on this volume. Strongest signal for GUI apps.

**2. LaunchServices database (all registered apps)**
`lsregister -dump` — every app registered with macOS. Cross-reference with installed apps to find ghosts. `lsappinfo list` shows currently running apps.

**3. Shell history (CLI tools)**
Parse `~/.zsh_history` — extract command names, count frequency. A brew-installed CLI tool that never appears in history is likely unused. Weight by recency.

**4. Homebrew dependency tree**
- `brew leaves` — top-level packages (explicitly installed)
- `brew autoremove --dry-run` — orphaned dependencies
- Cross-reference leaves with shell history: leaf + never used = candidate for removal

**5. pip/Python packages**
- `pip-autoremove -l` — list unused dependencies
- `pipdeptree` — dependency tree, find orphans
- `pip list --not-required` — packages nothing depends on

**Confidence scoring:**
- HIGH: kMDItemLastUsedDate > 180 days + not in shell history + no running processes
- MEDIUM: kMDItemLastUsedDate > 90 days OR brew leaf + not in history
- LOW: Only one signal present

For bulk queries: `mdfind -onlyin /Applications "kMDItemLastUsedDate < $NINETY_DAYS_AGO"` returns all stale apps in one call. Zero-dep approach: `subprocess.run(["mdls", ...])` — no need for osxmetadata package.

## Supporting Evidence

> **Evidence: [HIGH]** — https://developer.apple.com/forums/thread/20639, https://eclecticlight.co/2019/03/25/lsregister-a-valuable-undocumented-command-for-launchservices/, https://medium.com/@connorbworley/cleaning-up-unused-homebrew-packages-147e32724646, https://github.com/invl/pip-autoremove, retrieved 2026-03-22

## Caveats

None identified yet.
