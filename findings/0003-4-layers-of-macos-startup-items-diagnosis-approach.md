---
id: '0003'
title: 4 layers of macOS startup items — diagnosis approach
status: open
evidence: HIGH
sources: 1
created: '2026-03-22'
---

## Claim

macOS has 4 distinct layers where startup items live. Each needs different detection:

**1. Launch Daemons** (`/Library/LaunchDaemons/`, `/System/Library/LaunchDaemons/`)
- Run as root, start at boot before any user logs in
- System-level services: DNS, Bluetooth, Spotlight
- Third-party ones are the problem: antivirus, VPN, management agents
- Detection: `launchctl list` + cross-reference with known Apple services

**2. Launch Agents** (`~/Library/LaunchAgents/`, `/Library/LaunchAgents/`)
- Run as user, start at login
- This is where crash-looping watchman lived
- Detection: parse plist files, check `KeepAlive`, check `launchctl list` exit codes
- apple-a-day already does basic crash-loop detection here

**3. Login Items** (System Settings → General → Login Items)
- Apps that open at login
- macOS 13+ uses SMAppService framework
- Detection: `osascript -e 'tell application "System Events" to get the name of every login item'`
- Or: `sfltool dumpbtm` (Background Task Management database, macOS 13+)

**4. Background Items** (macOS 13+ Background Items UI)
- Unified view of all background tasks
- `sfltool dumpbtm` dumps the full database — includes launch agents, login items, and SMAppService registrations
- This is the most complete single source on modern macOS

**For diagnosis, cross-reference with:**
- `ps aux --sort=-%mem` — what's actually eating RAM right now
- `ps aux --sort=-%cpu` — what's eating CPU
- `launchctl list` exit codes — non-zero = crashing/broken

**Where this lives:** Split between apple-a-day (diagnosis) and space-hog (removal). apple-a-day answers "what's wrong", space-hog answers "remove it."

## Supporting Evidence

> **Evidence: [HIGH]** — https://medium.com/@durgaviswanadh/understanding-macos-launchagents-and-login-items-a-clear-practical-guide-5c0e39e3a6b3, https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html, https://www.makeuseof.com/tag/hidden-launchdaemons-launchagents-mac/, retrieved 2026-03-22

## Caveats

None identified yet.
