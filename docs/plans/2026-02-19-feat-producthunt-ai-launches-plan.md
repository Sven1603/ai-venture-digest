---
title: "Add Product Hunt as AI Launch Source"
type: feat
date: 2026-02-19
---

# Add Product Hunt as AI Launch Source

## Overview

Add Product Hunt's RSS feed as a new content source to surface practical AI tool launches for the target audience (vibe coders, solopreneurs, indie hackers). Launches appear in a distinct "Product Launches" category with a rocket badge and emoji, giving them visibility without blending into existing articles.

## Motivation

Product Hunt is where the target audience discovers new tools. AI product launches are a natural fit for the digest — they're inherently actionable ("try this new tool") and complement existing content types (tutorials, deep dives, podcasts).

## Technical Approach

Follow existing fetch function patterns exactly. Four files change.

### 1. `config.json` — Add source entry

Add a new `"producthunt"` key under `sources` (NOT inside `rss_feeds` — that would cause `fetch_engineering_blogs()` to also process it with the wrong filter).

```json
"producthunt": [
  {
    "name": "Product Hunt",
    "url": "https://www.producthunt.com/feed",
    "reputation": 0.85
  }
]
```

Reputation 0.85 — on par with The Verge and The Neuron. Signal-to-noise is lower than curated blogs, but the keyword filter compensates.

### 2. `scripts/fetcher.py` — Add fetch function and integrate

**a) Add `fetch_producthunt()` function** (after `fetch_twitter_posts`, before scoring section ~line 540)

Follow the standard pattern: print emoji header → loop sources → fetch RSS → apply keyword filter → set category/content_type → append → print summary.

```python
def fetch_producthunt(config):
    """Fetch AI product launches from Product Hunt."""
    print("\n🚀 Fetching Product Hunt launches...")
    launches = []

    sources = config['sources'].get('producthunt', [])

    for source in sources:
        name = source['name']
        url = source['url']
        reputation = source['reputation']

        try:
            items = fetch_rss(url, name, reputation, 'product_launch')
            accepted = 0

            for item in items:
                title = item['title']
                desc = item.get('description', '')
                text = (title + ' ' + desc).lower()

                # AI keyword filter (word-boundary-safe)
                ai_keywords = [
                    ' ai ', ' ai-', 'gpt', 'llm', 'automation',
                    'no-code', 'copilot', 'agent', 'chatbot',
                ]

                if any(kw in f' {text} ' for kw in ai_keywords):
                    item['category'] = 'launch'
                    item['content_type'] = 'product_launch'
                    launches.append(item)
                    accepted += 1
                    print(f"  ✓ {name}: {title[:50]}...")

            if accepted == 0:
                print(f"  - {name}: No AI launches found")

        except Exception as e:
            print(f"  ⚠ {name}: {e}")

    print(f"  → Found {len(launches)} AI product launches")
    return launches
```

**Keyword filter design decisions:**
- Uses `' ai '` and `' ai-'` (with spaces) instead of bare `'ai'` to avoid substring false positives ("email", "domain", "contain"). The `f' {text} '` padding ensures word boundaries at start/end of string.
- Removed "productivity", "workflow" — too many false positives (non-AI productivity tools).
- Removed "machine learning" — targets ML engineers, not vibe coders.
- Removed "artificial intelligence" (rare in PH copy) and "ai-powered" (redundant with `' ai-'`).
- No separate filter function — inline check matches the Twitter fetcher pattern (lines 456-460).
- Does NOT run `is_actionable_content()` — product launches are inherently announcements, which the strict actionable filter would block. The AI keyword filter is the right gate.

**b) Add `product_launch` to `type_bonuses`** in `calculate_score()` (~line 563):

```python
type_bonuses = {
    'tutorial': 0.25,
    'deep_dive': 0.20,
    'skill': 0.20,
    'tool_demo': 0.15,
    'product_launch': 0.12,  # ← ADD
    'tool_update': 0.10,
    'podcast': 0.12
}
```

**c) Call from `main()`** after Twitter/before scoring (~line 729):

```python
# 6. Product Hunt launches
ph_launches = fetch_producthunt(config)
all_articles.extend(ph_launches)
```

**d) Fix Atom `<content>` parsing in `fetch_rss()`** (~line 188):

**Critical issue found by SpecFlow:** Product Hunt uses Atom `<content type="html">` for taglines, not `<summary>`. The current `fetch_rss()` only checks `description` and `{Atom}summary`, so every Product Hunt entry will have an **empty description**. This breaks keyword filtering accuracy and display quality.

Fix: add `{http://www.w3.org/2005/Atom}content` as a third fallback:

```python
# Current (line 188):
description = item.findtext('description') or item.findtext('{http://www.w3.org/2005/Atom}summary') or ''

# Fixed:
description = (item.findtext('description')
               or item.findtext('{http://www.w3.org/2005/Atom}summary')
               or item.findtext('{http://www.w3.org/2005/Atom}content')
               or '')
```

This is a safe change — for all existing sources, `description` or `{Atom}summary` will match first. The new fallback only triggers for Atom feeds that use `<content>` (like Product Hunt). Note: Atom `<content>` may contain HTML markup, but the existing `re.sub(r'<[^>]+>', '', description)` at line 198 strips it safely.

**e) Add Atom `<updated>` fallback for date parsing** in `fetch_rss()` (~line 189):

Product Hunt's Atom feed may use `<updated>` instead of `<published>`. Without this fallback, recency scoring defaults to a mediocre 0.3 multiplier.

```python
# Current:
pub_date = item.findtext('pubDate') or item.findtext('{http://www.w3.org/2005/Atom}published') or ''

# Fixed:
pub_date = (item.findtext('pubDate')
            or item.findtext('{http://www.w3.org/2005/Atom}published')
            or item.findtext('{http://www.w3.org/2005/Atom}updated')
            or '')
```

Same safe fallback pattern — existing feeds match earlier in the chain.

**f) Add launch articles to Quick Wins eligibility** in `create_quick_wins()` (~line 611):

Product Hunt launches are literally new tools — they should be eligible for the "New Tool" Quick Win slot.

```python
# Current:
tools = [a for a in articles if a.get('category') in ['tools'] or a.get('content_type') in ['tool_demo', 'tool_update']]

# Updated:
tools = [a for a in articles if a.get('category') in ['tools', 'launch'] or a.get('content_type') in ['tool_demo', 'tool_update', 'product_launch']]
```

### 3. `index.html` — Add badge style and emoji

**a) Add `.category-badge.launch` CSS** (after `.category-badge.video`, ~line 354):

```css
.category-badge.launch { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
```

Red-ish color — connotes urgency/newness, distinct from all existing badge colors.

**b) Add `launch` to `getCategoryEmoji()`** (~line 783):

```javascript
launch: '🚀',
```

### 4. `scripts/newsletter.py` — Add category display info

Add to `category_info` dict (~line 60):

```python
'launch': {'emoji': '🚀', 'title': 'Product Launches'},
```

## What NOT to change

- **No dedicated website section** — launches appear in Must Reads and More Updates with badge differentiation. A dedicated section would be premature for a single-source category.
- **No `priorityCategories` boost** — launches should earn their way into Top 5 Must Reads on base score alone. The 0.12 type bonus is sufficient for them to surface without dominating.
- **No fallback content** — unlike Twitter (which has `get_default_twitter_posts()`), Product Hunt is supplementary. If the feed is down, the digest simply has fewer items.

## Acceptance Criteria

- [x] `config.json`: `producthunt` source entry with URL and reputation 0.85
- [x] `fetcher.py`: `fetch_producthunt()` function with word-boundary-safe AI keyword filter
- [x] `fetcher.py`: `product_launch` in `type_bonuses` dict with 0.12 bonus
- [x] `fetcher.py`: `fetch_producthunt()` called from `main()`
- [x] `fetcher.py`: `fetch_rss()` handles Atom `<content>` element as description fallback
- [x] `fetcher.py`: `fetch_rss()` handles Atom `<updated>` element as date fallback
- [x] `fetcher.py`: `create_quick_wins()` includes `launch`/`product_launch` in tool candidates
- [x] `index.html`: `.category-badge.launch` CSS rule with red color
- [x] `index.html`: `launch: '🚀'` in `getCategoryEmoji()`
- [x] `newsletter.py`: `'launch'` entry in `category_info` dict
- [x] Pipeline runs without errors (`python3 scripts/fetcher.py`)
- [x] Product Hunt launches appear in `data/articles.json` with correct category/content_type
- [ ] Launch badge renders correctly on website (visual verification pending)

## Context & References

### Internal References
- Brainstorm: `docs/brainstorms/2026-02-19-producthunt-integration-brainstorm.md`
- Existing fetch patterns: `scripts/fetcher.py:243-488` (YouTube, podcasts, blogs, Twitter)
- Scoring: `scripts/fetcher.py:546-594`
- Quick Wins: `scripts/fetcher.py:601-661`
- Badge styles: `index.html:348-354`
- Emoji map: `index.html:774-785`
- Newsletter categories: `scripts/newsletter.py:54-60`
- Source diversity learning: `docs/solutions/logic-errors/source-concentration-and-display-quality.md`
- Config commit learning: `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md`

### Key Gotchas (from institutional learnings)
- **Config + code must ship together** — commit `config.json` changes with `fetcher.py` changes
- **`max_per_source` is 2** (not 3 as brainstorm stated) — Product Hunt capped at 2 articles per run
- **Dedup is automatic** — `seen_urls.json` prevents repeat launches across days
- **Atom feeds use `<content>` not `<summary>`** — `fetch_rss()` needs the fallback fix
- **Atom feeds may use `<updated>` not `<published>`** — `fetch_rss()` needs a date fallback too
- **Bare `'ai'` substring matching is broken** — use `' ai '`/`' ai-'` with space padding for word boundaries
