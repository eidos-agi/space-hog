---
id: TASK-0008
title: Login items audit via osascript + SMAppService
status: To Do
created: '2026-03-22'
priority: medium
milestone: MS-0002
tags:
  - research-0003
  - startup-health
definition-of-done:
  - Lists all login items with app name and enabled state
  - Cross-references with kMDItemLastUsedDate
  - Suggests removal for unused login items
---
Query login items via osascript ('tell application "System Events" to get login items'). Cross-reference with app usage to find login items for apps you rarely use. Suggest removal with launchctl bootout or System Settings path.
