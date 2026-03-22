---
id: TASK-0001
title: Spotlight-based unused GUI app detection
status: Done
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
updated: '2026-03-22'
---
Use mdls kMDItemLastUsedDate to find GUI apps not opened in 90+ days. Bulk query via mdfind -onlyin /Applications for speed. Show app name, size, last used date. This is the strongest single signal.

**Completion notes:** Existing app detection via mdls already worked. Enhanced with mdfind bulk query in the new unused.py module. Wired into --unused flag.
