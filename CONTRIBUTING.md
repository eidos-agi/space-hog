# Contributing to Space Hog

Thanks for helping reclaim disk space.

## Quick start

```bash
git clone https://github.com/eidos-agi/space-hog.git
cd space-hog
pip install -e .
space-hog --help
```

## Adding a new scanner

Each scanner lives in `space_hog/` as a function. The pattern:

1. Scan a location using native macOS tools or stdlib
2. Return structured results (dict with `name`, `size_bytes`, `command`, `risk_score`)
3. Register in `advisor.py` → `collect_cleanup_opportunities()`

## Rules

1. **Mac-only.** Use macOS-specific paths and tools.
2. **Zero dependencies.** Stdlib Python only.
3. **Safety first.** Every cleanup has a `risk_score` (1=safe, 2=moderate, 3=caution). Never auto-delete.
4. **Agent-friendly.** Output structured data. No interactive prompts.

## Pull requests

- One feature per PR
- Test on your own Mac first
- Include example output showing what your change finds
