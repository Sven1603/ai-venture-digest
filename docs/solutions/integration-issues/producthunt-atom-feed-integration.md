---
title: Product Hunt Atom feed integration — keyword filtering, Atom parsing, and per-source caps
category: integration-issues
module: config.json, scripts/fetcher.py, index.html, scripts/newsletter.py
tags: [producthunt, atom, rss, keyword-filter, word-boundary, source-caps, content-type]
symptoms:
  - "Product Hunt entries have empty descriptions despite feed containing taglines"
  - "Bare 'ai' substring match causes false positives (email, domain, contain)"
  - "Only 2 Product Hunt launches appear despite 5+ in feed"
  - "Product Hunt launches get default 0.3 recency score instead of actual date"
  - "Product Hunt pages return 403 — no logo/thumbnail extraction possible"
root_cause: Atom feeds use <content> not <summary>, bare substring matching hits false positives, default max_per_source cap too low for targeted sources
date_solved: 2026-02-19
severity: medium
---

# Product Hunt Atom feed integration

## Problem

Adding Product Hunt as a new content source required solving several issues that weren't visible with existing RSS/Atom sources:

1. Product Hunt entries had **empty descriptions** — keyword filtering matched only titles, missing AI launches with keywords only in taglines
2. **Bare `'ai'` substring** in keyword filter matched "email", "domain", "contain", "fair" — too many false positives
3. Default `max_per_source: 2` was too restrictive for a source specifically targeted for AI launches
4. Product Hunt Atom dates use `<updated>` not `<published>` — recency scoring defaulted to 0.3
5. Product Hunt blocks all page scraping (403 on every endpoint) — no logo extraction possible

## Root Causes

### Empty descriptions from Atom `<content>`

The `fetch_rss()` fallback chain was:
```python
description = item.findtext('description') or item.findtext('{http://www.w3.org/2005/Atom}summary') or ''
```

Product Hunt's Atom feed uses `<content type="html">` for taglines, not `<summary>`. Every entry got an empty string.

### Word-boundary failures in keyword matching

The original approach used bare substring checks like `'ai' in text`. This matches any string containing "ai" — "email", "domain", "contain", etc. Product Hunt listings for email tools, domain registrars, and productivity apps would all false-positive into the AI category.

### Per-source cap too rigid

The global `max_per_source: 2` made sense for generic RSS feeds where variety matters. But Product Hunt is already filtered to AI-only launches — capping at 2 discards valid content. Sources with targeted filtering need higher caps.

### Missing Atom `<updated>` date fallback

Same pattern as the description issue — `fetch_rss()` only checked `pubDate` and `{Atom}published`, missing `{Atom}updated` which Product Hunt uses. Without a parsed date, `calculate_recency()` returns 0.3 instead of the actual time-based score.

## Solution

### 1. Atom `<content>` fallback in `fetch_rss()`

```python
# scripts/fetcher.py — fetch_rss() description parsing
description = (item.findtext('description')
               or item.findtext('{http://www.w3.org/2005/Atom}summary')
               or item.findtext('{http://www.w3.org/2005/Atom}content')
               or '')
```

Safe for all existing sources — `description` or `{Atom}summary` match first. The `<content>` fallback only triggers for Atom feeds using it (like Product Hunt). HTML in `<content>` is stripped by the existing `re.sub(r'<[^>]+>', '', description)` downstream.

### 2. Atom `<updated>` fallback for date parsing

```python
# scripts/fetcher.py — fetch_rss() date parsing
pub_date = (item.findtext('pubDate')
            or item.findtext('{http://www.w3.org/2005/Atom}published')
            or item.findtext('{http://www.w3.org/2005/Atom}updated')
            or '')
```

Same safe fallback pattern — existing feeds match earlier in the chain.

### 3. Word-boundary-safe keyword filtering

```python
# scripts/fetcher.py — fetch_producthunt()
ai_keywords = [
    ' ai ', ' ai-', 'gpt', 'llm', 'automation',
    'no-code', 'copilot', 'agent', 'chatbot',
]

if any(kw in f' {text} ' for kw in ai_keywords):
    item['category'] = 'launch'
    item['content_type'] = 'product_launch'
```

The `f' {text} '` padding adds spaces at start/end so `' ai '` matches "an ai tool" but not "email". The `' ai-'` variant catches "ai-powered", "ai-driven" without a separate keyword.

**Removed keywords** (too many false positives or wrong audience):
- `'productivity'`, `'workflow'` — matches non-AI productivity tools
- `'machine learning'` — targets ML engineers, not vibe coders
- `'artificial intelligence'` — rare in PH copy
- `'ai-powered'` — redundant with `' ai-'`

### 4. Per-source cap overrides

```json
// config.json — filters section
"source_caps": {
    "Product Hunt": 5
}
```

```python
# scripts/fetcher.py — diversity filter
max_per_source = config['filters'].get('max_per_source', 3)
source_caps = config['filters'].get('source_caps', {})
for article in all_articles:
    src = article.get('source', 'unknown')
    cap = source_caps.get(src, max_per_source)
    source_counts[src] = source_counts.get(src, 0) + 1
    if source_counts[src] <= cap:
        diverse_articles.append(article)
```

Sources with targeted filtering (like Product Hunt's AI keyword gate) get higher caps. Generic sources keep the default.

### 5. Config placement

Product Hunt source goes under its own `"producthunt"` key in `config.json`, **not** inside `"rss_feeds"`. Placing it in `rss_feeds` would cause `fetch_engineering_blogs()` to also process it with the wrong content filter.

### 6. Logo/thumbnail extraction — not possible

Product Hunt returns 403 on all page scraping attempts (tried multiple User-Agent strings, direct URLs, og:image extraction). The UI uses a rocket emoji fallback icon instead. If PH ever adds image URLs to their Atom feed, the `index.html` template already supports a `thumbnail` field.

## Prevention

### 1. Test Atom feeds for field names before assuming RSS compatibility

Different Atom feeds use different elements (`<summary>` vs `<content>`, `<published>` vs `<updated>`). Always inspect the actual feed XML before integrating. The safe pattern is a multi-element fallback chain.

### 2. Never use bare substring matching for short keywords

Any keyword under 4 characters risks false positives. Use space-padding (`f' {text} '`) or regex word boundaries. Test against common words that contain the substring.

### 3. Per-source caps belong in config, not code

When a new source has different filtering characteristics than existing sources, add a `source_caps` override rather than changing the global `max_per_source`. This keeps the diversity guarantee for generic sources while allowing targeted sources to contribute more.

### 4. Clear dedup history when re-testing

`seen_urls.json` prevents the same article from appearing twice across runs. When testing a new source, URLs from test runs will block future runs. Clear the source's URLs from `seen_urls.json` before production runs.

## Related

- `docs/solutions/logic-errors/source-concentration-and-display-quality.md` — original source diversity cap implementation that this feature extends with per-source overrides
- `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md` — config + code must ship together (applies here: `config.json` and `fetcher.py` changes are coupled)
- `docs/solutions/integration-issues/vercel-analytics-blocked-by-adblockers.md` — another integration where external service behavior required workarounds
- `docs/plans/2026-02-19-feat-producthunt-ai-launches-plan.md` — full implementation plan with acceptance criteria
- `docs/brainstorms/2026-02-19-producthunt-integration-brainstorm.md` — original brainstorm exploring the idea
