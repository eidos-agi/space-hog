---
id: TASK-0003
title: Homebrew orphan detection via brew autoremove
status: To Do
created: '2026-03-22'
priority: medium
milestone: MS-0001
tags:
  - research-0002
  - unused-detection
definition-of-done:
  - '--unused includes brew orphans in recommendations'
  - Shows size of each orphan
  - Risk score 1 (SAFE) for all orphans
---
Integrate brew autoremove --dry-run into space-hog's recommendations. Show orphaned dependencies with sizes and the command to remove them. Zero risk — these are deps whose parent was already uninstalled.
