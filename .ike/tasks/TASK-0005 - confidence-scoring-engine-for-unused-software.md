---
id: TASK-0005
title: Confidence scoring engine for unused software
status: To Do
created: '2026-03-22'
priority: high
milestone: MS-0001
tags:
  - research-0001
  - unused-detection
  - agent-native
definition-of-done:
  - Each unused item has a confidence score (HIGH/MEDIUM/LOW)
  - Score based on number of corroborating signals
  - '--unused --json outputs confidence field'
---
Combine all 5 signals into a confidence score per item. HIGH = multiple signals agree (last used > 180d + not in history + no running process). MEDIUM = one strong signal. LOW = one weak signal. Agent uses confidence to decide what to present to user.
