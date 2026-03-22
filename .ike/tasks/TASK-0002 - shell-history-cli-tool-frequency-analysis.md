---
id: TASK-0002
title: Shell history CLI tool frequency analysis
status: To Do
created: '2026-03-22'
priority: high
milestone: MS-0001
tags:
  - research-0001
  - unused-detection
definition-of-done:
  - Parses zsh_history for command frequency
  - Cross-references with brew leaves
  - 'Shows: package name, size, last used (from history), install date'
---
Parse ~/.zsh_history to extract command frequencies. Cross-reference with brew leaves to find Homebrew packages that were explicitly installed but never (or rarely) used. Weight by recency — a tool used 6 months ago but not since is a candidate.
