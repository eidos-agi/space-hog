---
id: TASK-0004
title: Python orphan package detection
status: To Do
created: '2026-03-22'
priority: low
milestone: MS-0001
tags:
  - research-0001
  - unused-detection
definition-of-done:
  - Detects orphan pip packages
  - Shows sizes
  - Suggests pip uninstall commands
---
Use pip list --not-required and pipdeptree (if available) to find Python packages nothing depends on. Show sizes. Lower priority because pyenv versions are the bigger Python space hog.
