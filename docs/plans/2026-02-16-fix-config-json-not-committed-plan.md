---
title: "Fix daily fetch crash: config.json not committed after fetcher rewrite"
type: fix
date: 2026-02-16
---

# Fix daily fetch crash: config.json not committed after fetcher rewrite

## Overview

The daily GitHub Actions fetch has been crashing every run with `KeyError: 'reputation_weight'` in `calculate_score()`. Root cause: `config.json` was updated locally to match the new fetcher format but never committed.

## Problem Statement

Commit `37a7f9f` ("Rewrite fetcher with weighted scoring and strict content filtering") rewrote `scripts/fetcher.py` to expect a **flat** `config.json` filters format:

```python
# scripts/fetcher.py:553 — expects flat keys
score += article.get('reputation', 0.5) * filters['reputation_weight']
```

But `config.json` was never committed with the matching changes. The committed version still has the **old nested** format:

```json
"filters": {
  "engagement": { "enabled": true, "weight": 0.3 },
  "reputation": { "enabled": true, "weight": 0.25 },
  ...
}
```

The fetcher expects the **new flat** format (present locally but unstaged):

```json
"filters": {
  "max_age_hours": 72,
  "max_articles": 30,
  "reputation_weight": 0.25,
  "relevance_weight": 0.30,
  "recency_weight": 0.20,
  "engagement_weight": 0.25,
  "strict_actionable": true
}
```

Additionally, the committed config has `topics` as a nested object (`{primary: [...], secondary: [...]}`) while the fetcher expects a flat array (`topics = config.get('topics', [])`).

## Fix

Commit the local `config.json` which already has the correct format. The diff covers:

1. **`filters` section** — flat weight keys (`reputation_weight`, `relevance_weight`, `recency_weight`, `engagement_weight`) replacing nested objects
2. **`topics` section** — flat array replacing nested object with `primary`/`secondary`/`examples` sub-arrays
3. **`sources` section** — updated feeds list with youtube, podcasts, github skills, twitter accounts, and nitter instances (matching what the rewritten fetcher iterates over)
4. **Removed sections** — `curation` and `newsletter` blocks that are no longer referenced by the rewritten fetcher

No code changes needed in `fetcher.py` — it already expects the new format.

## Acceptance Criteria

- [x] `config.json` committed with flat filter weights matching `fetcher.py` expectations
- [x] `python3 scripts/fetcher.py` runs locally without `KeyError`
- [ ] Daily GitHub Actions run succeeds (verify on next scheduled or manual trigger)

## Verification

```bash
# Local smoke test — should reach scoring without KeyError
python3 scripts/fetcher.py

# Or trigger CI manually after pushing
gh workflow run "Daily AI Digest Fetch"
```

## References

- Crash traceback: `KeyError: 'reputation_weight'` at `scripts/fetcher.py:553`
- Root cause commit: `37a7f9f` (rewrote fetcher but didn't commit config)
- File: `config.json` (local has correct version, committed version is stale)
