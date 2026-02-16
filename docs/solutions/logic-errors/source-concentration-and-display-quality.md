---
title: Source concentration, undefined display fields, and audience mismatch in digest output
category: logic-errors
tags: [config, diversity, display, audience, curation, sources, rss]
module: config.json, index.html, scripts/fetcher.py, scripts/newsletter.py
symptoms:
  - "'undefined' text visible in must-reads and quick wins on live site"
  - "DEEP_DIVE label showing on every must-read article"
  - "9 of 30 articles from same source (n8n Blog)"
  - "Internal float score (0.7124...) displayed to readers"
  - "Content too engineering-focused for target audience"
root_cause: No per-source cap, uncommitted index.html fixes, engineering-biased config
date_solved: 2026-02-16
severity: medium
---

# Source concentration, undefined display fields, and audience mismatch

## Problem

After fixing the CI pipeline crash, the digest was running but the output had multiple quality issues visible to readers:

1. "undefined" text in must-reads where author/read time should be
2. Every must-read labeled "DEEP_DIVE" — the only category blog posts ever get
3. 9/30 articles from n8n Blog, 9 from James Briggs — massive source concentration
4. Internal score like `0.7124999999999999` shown in newsletter emails
5. Content skewed toward engineering (RAG, embeddings, LangChain) while the audience is vibe coders and marketing people

## Root Causes

### "undefined" in display

The deployed `index.html` referenced fields the fetcher doesn't produce:

| Used in index.html | Actual field from fetcher | Result |
|---|---|---|
| `a.summary` | `a.description` | "undefined" |
| `a.readTime` (no fallback) | not produced | "undefined min" |

Local copy had fixes but — same pattern as the config crash — they were never committed.

### Category labels always "deep_dive"

`fetch_engineering_blogs()` in `fetcher.py:352` classifies all articles passing `is_actionable_content()` as `content_type: 'deep_dive'`. There's no finer classification. Since must-reads are all blog posts, they all get the same label.

### Source concentration

No `max_per_source` cap existed. With only 6 RSS feeds and 9 YouTube channels, prolific sources filled most of the 30-article limit.

### Audience mismatch

The `topics` list included engineering terms (`rag`, `embeddings`, `vector database`, `langgraph`) that boosted relevance scoring for technical content. The RSS feed list was only 6 sources, skewing toward engineering blogs. Two YouTube channels (Sam Witteveen, James Briggs) were LangChain-focused with high reputation scores.

## Solution

### Phase 1: Display fixes

```javascript
// index.html — must-reads template
// Before (shows "undefined"):
${a.summary}
${a.readTime} min

// After:
${a.description || a.summary || ''}
${a.readTime || 5} min
```

Removed category badge from must-reads entirely since it's always "deep dive."

### Phase 2: Score removal

Removed internal score from newsletter email (stats bar and per-article display) and plain text version. Replaced "TOP SCORE" stat with "TUTORIALS" count.

### Phase 3: Source diversity cap

Added per-source cap in `fetcher.py` after scoring, before the article limit:

```python
# fetcher.py — after sort by score, before quick wins
max_per_source = config['filters'].get('max_per_source', 2)
source_counts = {}
diverse_articles = []
for article in all_articles:
    src = article.get('source', 'unknown')
    source_counts[src] = source_counts.get(src, 0) + 1
    if source_counts[src] <= max_per_source:
        diverse_articles.append(article)
all_articles = diverse_articles
```

### Phase 4: Audience-appropriate sources and topics

`config.json` changes:

- **RSS feeds**: 6 → 14 (added TechCrunch AI, The Verge AI, OpenAI Blog, Google AI Blog, Anthropic Blog, Ben's Bites, The Neuron, Lenny's Newsletter)
- **Topics removed**: `rag`, `embeddings`, `vector database`, `langgraph`
- **Topics added**: `vibe coding`, `no-code`, `low-code`, `ai writing`, `chatgpt`, `gemini`, `ai productivity`
- **YouTube**: Lowered reputation for LangChain-focused channels (0.9 → 0.75)
- **max_per_source**: Set to 2

Result: 14 unique sources in output (was 12 with cap of 3, was 3-4 dominant sources with no cap).

## Prevention

### 1. Always check display with real data

After changing data schemas, open the site with actual fetcher output — not just hardcoded fallback data. Fields that exist in fallback data but not in fetcher output cause "undefined" in production.

### 2. Config changes need audience review

When adding sources or topics, ask: "Would a marketing person or vibe coder care about this?" If the answer is no, it doesn't belong in the config.

### 3. Source diversity is a config concern

Any new source added should come with a check: does `max_per_source` still produce good variety? Run the fetcher locally and check `Counter(a['source'] for a in articles)`.

## Related

- `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md` — the CI crash that preceded these quality fixes
- `docs/brainstorms/2026-02-16-source-diversity-and-audience-fit-brainstorm.md` — brainstorm on audience and sources
- `docs/plans/2026-02-16-feat-source-diversity-and-audience-fit-plan.md` — implementation plan

## Commits

- `5b1a1ff` fix: resolve undefined fields, raw categories, and source concentration
- `332b229` Remove internal score from newsletter display
- `11bca75` Remove top score from email header, remove category badge from must-reads
- `634bb14` feat: expand source diversity and tune for non-technical audience
