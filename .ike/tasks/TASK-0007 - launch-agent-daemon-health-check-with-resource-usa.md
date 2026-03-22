---
id: TASK-0007
title: Launch agent/daemon health check with resource usage
status: To Do
created: '2026-03-22'
priority: high
milestone: MS-0002
tags:
  - research-0003
  - startup-health
definition-of-done:
  - 'Shows resource usage per startup item (CPU%, RSS)'
  - Flags crash-looping items (non-zero exit + KeepAlive)
  - Flags orphaned agents (plist but no parent app)
  - Risk scores for each recommended action
---
Cross-reference launchctl list (exit codes) with ps aux (CPU/memory) to find startup items that are: crash-looping (non-zero exit + KeepAlive), resource-hogging (high CPU/RAM), or orphaned (plist exists but parent app uninstalled). This extends apple-a-day's crash-loop detection into a full startup audit.
