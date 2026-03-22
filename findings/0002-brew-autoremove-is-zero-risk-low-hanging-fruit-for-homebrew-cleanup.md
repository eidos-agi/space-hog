---
id: '0002'
title: brew autoremove is zero-risk low-hanging fruit for Homebrew cleanup
status: open
evidence: HIGH
sources: 1
created: '2026-03-22'
---

## Claim

`brew autoremove` removes formulae that were only installed as dependencies and are now orphaned. Built into Homebrew, not a third-party tool. Only removes dependency-installed packages — never things explicitly installed. Safe to automate.

`brew leaves` shows top-level (explicitly installed) packages. Cross-referencing leaves with shell history frequency answers: "You installed X but haven't used it in Y days."

Workflow for space-hog:
1. `brew autoremove --dry-run` — show reclaimable orphans (safe, automated)
2. `brew leaves` cross-referenced with `~/.zsh_history` — find unused explicit installs
3. Present with sizes and confidence scores

## Supporting Evidence

> **Evidence: [HIGH]** — https://medium.com/@connorbworley/cleaning-up-unused-homebrew-packages-147e32724646, https://pawelgrzybek.com/remove-unused-brew-dependencies-and-delete-outdated-downloads/, retrieved 2026-03-22

## Caveats

None identified yet.
