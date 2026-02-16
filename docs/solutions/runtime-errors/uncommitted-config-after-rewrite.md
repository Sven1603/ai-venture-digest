---
title: Uncommitted config.json after fetcher rewrite caused cascading CI failures
category: runtime-errors
tags: [config, ci, keyerror, deploy, newsletter, fetcher]
module: scripts/fetcher.py, scripts/newsletter.py, index.html
symptoms:
  - "KeyError: 'reputation_weight' in calculate_score"
  - "KeyError: 'newsletter' in generate_newsletter_html"
  - "KeyError: 'summary' in newsletter template"
  - "undefined" text visible on live website
  - "json.decoder.JSONDecodeError: Expecting value" from Mailchimp send
  - "Permission denied to github-actions[bot]" on git push
root_cause: Fetcher rewrite committed code changes but not the matching config.json updates
date_solved: 2026-02-16
severity: critical
---

# Uncommitted config.json after fetcher rewrite caused cascading CI failures

## Problem

The daily GitHub Actions pipeline (`Daily AI Digest Fetch`) crashed every run after commit `37a7f9f` ("Rewrite fetcher with weighted scoring and strict content filtering"). The fetcher was rewritten to expect a flat `config.json` structure, but the matching config changes were only saved locally — never committed. CI ran old config + new code = crash.

## Symptoms

```
KeyError: 'reputation_weight'
  File "scripts/fetcher.py", line 553, in calculate_score
    score += article.get('reputation', 0.5) * filters['reputation_weight']
```

## Root Cause

Commit `37a7f9f` changed `fetcher.py` to expect:

```json
"filters": {
  "reputation_weight": 0.25,
  "relevance_weight": 0.30,
  "recency_weight": 0.20,
  "engagement_weight": 0.25
}
```

But the committed `config.json` still had the old nested format:

```json
"filters": {
  "reputation": { "enabled": true, "weight": 0.25 },
  "engagement": { "enabled": true, "weight": 0.30 }
}
```

The local working copy had the correct config, making it work on the developer's machine but fail in CI.

## Cascading Failures

Fixing the initial KeyError exposed five more issues — all caused by the same "local changes not committed" pattern:

| # | Error | Cause | Fix |
|---|-------|-------|-----|
| 1 | `KeyError: 'reputation_weight'` | config.json filters not committed | Commit config.json |
| 2 | `KeyError: 'newsletter'` | newsletter section removed from new config | Restore newsletter section |
| 3 | `KeyError: 'summary'` | Fetcher produces `description`, newsletter used `summary` | Use `description` field |
| 4 | `JSONDecodeError` on Mailchimp send | Mailchimp returns 204 (empty body), code did `json.loads("")` | Handle empty responses |
| 5 | `Permission denied` on git push | Workflow missing `contents: write` | Add permissions block |
| 6 | "undefined" on website | Committed index.html used `a.summary` and `a.readTime` | Commit local fixes with fallbacks |

## Solution

Each fix was a small, focused commit pushed directly to main:

1. **`config.json`** — committed the flat format matching the rewritten fetcher
2. **`config.json`** — restored `newsletter` section needed by `newsletter.py`
3. **`newsletter.py`** — `item['summary']` → `item.get('description', '')`
4. **`newsletter.py`** — `json.loads(body) if body else {}`
5. **`daily-fetch.yml`** — added `permissions: contents: write`
6. **`index.html`** — committed local version with proper fallbacks

## Additional Quality Fixes (same session)

Once the pipeline was green, we addressed output quality:

- **Source concentration**: Added `max_per_source: 3` cap in fetcher to prevent any single source dominating (was 9/30 from n8n Blog)
- **Score display**: Removed internal float scores from newsletter (meaningless to readers)
- **Category labels**: Removed "deep dive" badge from must-reads since blog content is nearly always classified as `deep_dive`

## Prevention

### 1. Always test CI after multi-file rewrites

When rewriting a component that reads config, check:
- Did the config format change?
- Are all changed files staged? (`git diff --name-only` vs `git diff --staged --name-only`)
- Does the pipeline pass end-to-end, not just the changed script?

### 2. Field name contract between scripts

`fetcher.py` produces article dicts consumed by `newsletter.py` and `index.html`. There's no shared schema — field names are implicit. When renaming fields (e.g., `summary` → `description`), grep all consumers:

```bash
grep -rn "summary\|readTime\|score" scripts/ index.html
```

### 3. Mailchimp API responses

Mailchimp action endpoints (`/actions/send`, `/actions/schedule`) return `204 No Content`. Always handle empty response bodies when parsing JSON from HTTP APIs.

### 4. GitHub Actions permissions

Workflows that push commits back to the repo need explicit `permissions: contents: write`. The default token is read-only for workflows triggered by `schedule` and `workflow_dispatch`.

## Related Commits

- `2a2e293` fix: commit config.json matching rewritten fetcher format
- `1674382` fix: restore newsletter config section needed by newsletter.py
- `3380373` fix: use 'description' field in newsletter matching fetcher output
- `6d91b8e` fix: handle empty Mailchimp API responses (204 No Content)
- `611bc92` fix: grant write permissions to workflow for data commit step
- `5b1a1ff` fix: resolve undefined fields, raw categories, and source concentration

## Key Takeaway

A single uncommitted file caused a chain of 6 failures. The "works on my machine" problem is especially insidious with config files — the code runs locally because the local config is correct, while CI uses the stale committed version. Always verify `git status` after a rewrite and before pushing.
