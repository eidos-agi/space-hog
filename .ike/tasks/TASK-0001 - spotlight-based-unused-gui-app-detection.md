---
id: TASK-0001
title: Spotlight-based unused GUI app detection
status: To Do
created: '2026-03-22'
priority: high
milestone: MS-0001
tags:
  - research-0001
  - unused-detection
definition-of-done:
  - '--unused flag lists apps not opened in 90+ days with sizes'
  - Uses mdls/mdfind (zero deps)
  - Shows last-used date for each app
---
Use mdls kMDItemLastUsedDate to find GUI apps not opened in 90+ days. Bulk query via mdfind -onlyin /Applications for speed. Show app name, size, last used date. This is the strongest single signal.
