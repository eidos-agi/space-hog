---
id: TASK-0006
title: sfltool dumpbtm startup item inventory (macOS 13+)
status: To Do
created: '2026-03-22'
priority: high
milestone: MS-0002
tags:
  - research-0004
  - startup-health
definition-of-done:
  - '--startup flag lists all background tasks from BTM database'
  - 'Shows: name, type, enabled/disabled, path'
  - Falls back to plist scanning on macOS < 13
---
Use sfltool dumpbtm to enumerate all background tasks registered with macOS. Parse output to extract: item name, bundle ID, type (agent/daemon/login item), enabled state, path. This is the single most complete source on macOS 13+. Fallback to plist scanning for older macOS.
