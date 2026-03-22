---
id: '0004'
title: sfltool dumpbtm is the single best source for startup items on macOS 13+
status: open
evidence: MODERATE
sources: 1
created: '2026-03-22'
---

## Claim

`sfltool dumpbtm` dumps the Background Task Management database introduced in macOS 13 (Ventura). This is the unified database that powers the "Login Items & Extensions" panel in System Settings.

It includes:
- Launch agents and daemons (both user and system)
- Login items (apps that open at login)
- SMAppService registrations (modern framework for background tasks)
- Bundle IDs, paths, and enabled/disabled state

This is more complete than manually scanning plist directories because it includes items registered via the new SMAppService API that don't necessarily have traditional plist files.

Requires no sudo for the user-level dump. This should be the primary data source for startup auditing on macOS 13+, with fallback to plist scanning for older macOS versions.

## Supporting Evidence

> **Evidence: [MODERATE]** — https://www.makeuseof.com/tag/hidden-launchdaemons-launchagents-mac/, https://mundobytes.com/en/How-to-use-launchagents-and-launchdaemons-on-macOS/, retrieved 2026-03-22

## Caveats

None identified yet.
