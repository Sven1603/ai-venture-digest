---
title: "Fix undefined fields, DEEP_DIVE labels, and source concentration"
type: fix
date: 2026-02-16
---

# Fix undefined fields, DEEP_DIVE labels, and source concentration

## Overview

Three related quality issues with today's digest output:

1. **"undefined" in must-reads and quick wins** — missing field fallbacks in the deployed `index.html`
2. **Raw `DEEP_DIVE` category labels** — categories display as raw snake_case instead of human-readable text
3. **Source concentration** — 9/30 articles from n8n Blog, 9 from James Briggs, no per-source cap
4. **LangChain over-representation** — "langchain" appears in topics, sources, YouTube channels, and Twitter — it scores well everywhere

## Problem 1: "undefined" in display

The **committed** `index.html` references fields the fetcher doesn't produce:

| Field used in index.html | Actual field from fetcher | Result |
|---|---|---|
| `a.summary` | `a.description` | Shows "undefined" |
| `a.readTime` (no fallback) | not produced | Shows "undefined min" |

**Locations** in committed `index.html`:
- Must-reads: `${a.summary}` and `${a.readTime} min`

The local `index.html` has partial fixes (e.g., `a.description || a.summary || ''`) but was never committed.

### Fix

In `index.html`, update must-reads template:
- `${a.summary}` → `${a.description || a.summary || ''}`
- `${a.readTime} min` → `${a.readTime || 5} min`

These fixes already exist in the local working copy — just need to be committed.

## Problem 2: Raw category labels

The must-reads show `deep_dive` as-is. The local `index.html` already has a fix: `a.category.replace('_', ' ')` — but it's not committed.

### Fix

Commit the local `index.html` which already handles this.

## Problem 3: Source concentration

There's **no per-source cap** in the fetcher. With only 6 RSS feeds and 9 YouTube channels, prolific sources dominate. Today's data:

```
9  n8n Blog        (3 of top 5 must-reads)
9  James Briggs    (YouTube — all LangChain tutorials)
5  Simon Willison  (2 of top 5 must-reads)
3  GitHub
2  Practical AI
1  @simonw
1  @AnthropicAI
```

### Fix

Add a `max_per_source` cap in `fetcher.py` after scoring, before the final `[:max_articles]` slice. This ensures no single source dominates the output.

In `scripts/fetcher.py`, after sorting by score (line ~713) and before creating quick wins (line ~717):

```python
# Cap articles per source for diversity
max_per_source = config['filters'].get('max_per_source', 3)
source_counts = {}
diverse_articles = []
for article in all_articles:
    src = article.get('source', 'unknown')
    source_counts[src] = source_counts.get(src, 0) + 1
    if source_counts[src] <= max_per_source:
        diverse_articles.append(article)
all_articles = diverse_articles
```

Add to `config.json` filters:
```json
"max_per_source": 3
```

## Problem 4: LangChain bias

LangChain is baked into multiple layers of the config, creating compounding bias:

1. **Topics** (line 7): `"langchain", "langgraph"` — boosts relevance score for any LangChain mention
2. **RSS feeds**: LangChain Blog as a dedicated source
3. **YouTube**: 2 channels focused on LangChain (Sam Witteveen, James Briggs)
4. **Twitter**: @LangChainAI account
5. **Fetcher keywords** (line 457): `'langchain'` in relevance matching

This isn't a bug — it's a config choice. But combined with no per-source cap, it means LangChain content takes disproportionate space.

### Fix

No code change needed beyond the per-source cap from Problem 3. Optionally, trim LangChain from the `topics` list if it shouldn't boost scoring for all sources. Keep LangChain Blog as a source — it'll just be capped at 3 articles like everything else.

## Acceptance Criteria

- [x] No "undefined" text visible in must-reads or quick wins on the live site
- [x] Categories display as human-readable text (e.g., "deep dive" not "deep_dive")
- [x] No single source has more than `max_per_source` articles in the output
- [x] `max_per_source` configurable in `config.json` (default: 3)
- [x] LangChain content still appears but doesn't dominate

## Files to change

1. **`index.html`** — commit existing local fixes for undefined fields and category formatting
2. **`scripts/fetcher.py`** — add per-source diversity cap after scoring
3. **`config.json`** — add `max_per_source: 3` to filters

## References

- `index.html:1088` (committed) — `${a.summary}` causing "undefined"
- `index.html:1092` (committed) — `${a.readTime}` causing "undefined min"
- `scripts/fetcher.py:713` — insertion point for diversity cap
- `config.json:65-73` — filters section
