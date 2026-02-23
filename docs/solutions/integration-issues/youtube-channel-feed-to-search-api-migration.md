---
title: "YouTube channel Atom feeds replaced with Data API v3 search — stale videos, rickrolls, topic monoculture"
category: integration-issues
module: scripts/fetcher.py, config.json, index.html, .github/workflows/daily-fetch.yml
tags: [youtube, data-api, rss, content-freshness, api-migration, rickroll, monoculture]
symptoms:
  - "YouTube videos in digest are 8 months old (June 2025 in February 2026)"
  - "Video ID iN1Xx8ca_8I redirects to Rick Astley (dead video, no liveness check)"
  - "Only 2 of 9 YouTube channels produce content passing filters — both LangChain-focused"
  - "100 youtube_search_queries in config.json are completely unused by backend"
  - "Hardcoded rickroll fallback videos (dQw4w9WgXcQ) mask empty fetch results"
root_cause: "Channel Atom RSS feeds return sparse, unvalidated results with no hard age cutoff; recency score floors at 0 but doesn't disqualify; hardcoded fallback videos hide the broken data pipeline"
date_solved: 2026-02-23
severity: high
---

# YouTube channel Atom feeds → Data API v3 search

## Problem

Three compounding failures in `fetch_youtube_tutorials()`:

1. **Stale content** — Both videos in the digest were from June 2025 (8 months old). The recency scoring floored at 0 but never disqualified old content entirely.
2. **Dead videos** — Video ID `iN1Xx8ca_8I` now redirects to Rick Astley. No liveness validation exists for channel feed entries.
3. **Topic monoculture** — Only 2 of 9 hardcoded channels produced content passing `is_actionable_content`/`is_tool_content` filters, both LangChain-focused from the lowest-reputation channels (0.75).
4. **Dead config** — `youtube_search_queries` (100 entries) existed in `config.json` but no code path read them.
5. **Masked failures** — Hardcoded `dQw4w9WgXcQ` fallback videos in `index.html` made it look like videos were loading even when the fetcher returned nothing useful.

## Root Causes

**Channel Atom feeds are inherently sparse.** YouTube's channel RSS feeds (`/feeds/videos.xml?channel_id=X`) return the most recent ~15 uploads regardless of age. With strict content filters (`is_actionable_content`), most entries are rejected, leaving only ancient tutorials.

**No hard age cutoff.** The scoring system penalizes old content with a lower recency score (approaching 0), but old content still competes with zero-engagement fresh content and can win.

**Small channel pool + strict filters = monoculture.** 9 channels × ~15 entries each × strict filters = only 2 channels producing any output. Both happened to be LangChain-focused.

**Fallback defaults hide broken pipelines.** The frontend filled missing videos with hardcoded rickroll URLs, so the digest always appeared to have 3 videos even when the fetcher returned nothing.

## Solution

### 1. New `fetch_youtube_search(config)` in `scripts/fetcher.py`

Replaced channel Atom feeds with YouTube Data API v3 `search.list`:

```python
def fetch_youtube_search(config):
    api_key = os.environ.get('YOUTUBE_API_KEY', '')
    if not api_key:
        print("  ⚠ YOUTUBE_API_KEY not set — skipping YouTube search")
        return []

    # Deterministic daily selection (reproducible CI reruns)
    random.seed(datetime.utcnow().strftime('%Y-%m-%d'))
    selected = random.sample(queries, min(3, len(queries)))

    published_after = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
```

Key behaviors:
- **3 random queries per day**, seeded by date string for reproducible CI reruns
- **7-day `publishedAfter` cutoff** — hard freshness guarantee at the API level
- **HTTP 403 breaks the loop** — quota exhausted or key disabled, don't waste remaining queries
- **Existing filters applied** — `is_actionable_content` / `is_tool_content`, same as before
- **Graceful degradation** — missing API key or API failure returns `[]`, pipeline continues

API parameters:
```
part=snippet, type=video, maxResults=10, order=date,
publishedAfter={7d ago}, relevanceLanguage=en
```

Quota: 3 queries × 100 units = 300/day (3% of 10,000 free tier).

### 2. Config changes in `config.json`

- **Removed** `sources.youtube_channels` array (9 hardcoded channels)
- **Trimmed** `youtube_search_queries` from 100 → 25 distinct queries, cutting duplicates:
  - 10 "claude code *" → 3 kept
  - 8 "cursor ai *" → 3 kept
  - 9 "langchain *" → 2 kept
  - 7 generic "build ai *" → 2 kept
  - Unique topic queries preserved (n8n, prompt engineering, voice AI, etc.)

### 3. Frontend empty state in `index.html`

Replaced rickroll fallback videos with an empty state:

```javascript
if (videos.length === 0) {
    grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 2rem 1rem; opacity: 0.7;">
            <p style="font-size: 1.1rem;">No fresh tutorials today</p>
            <p style="font-size: 0.9rem;">Check back tomorrow or browse YouTube directly below.</p>
        </div>`;
    return;
}
```

Also synced `getDailyYouTubeSearchQuery()` query list to match the trimmed 25.

### 4. GitHub Actions workflow

Added `YOUTUBE_API_KEY` env var to the fetcher step in `.github/workflows/daily-fetch.yml`.

## Critical constraint: ship together

All 4 files (`fetcher.py`, `config.json`, `index.html`, `daily-fetch.yml`) must be committed and deployed together. See [uncommitted-config-after-rewrite](../runtime-errors/uncommitted-config-after-rewrite.md) for the documented pattern of config/code decoupling causing cascading CI failures.

## Article dict contract

`video_url` **must** be truthy on all YouTube articles. The frontend uses `!a.video_url` to exclude videos from Must Reads (`index.html`, `renderMustReads()`). Missing `video_url` = videos leak into Must Reads.

```python
video_url = f"https://www.youtube.com/watch?v={video_id}"
videos.append({
    'url': video_url,
    'video_url': video_url,  # MUST be set — not None
    'source': snippet.get('channelTitle', 'YouTube'),  # channel name, not "YouTube"
    'reputation': 0.85,  # below curated feeds (0.9-1.0)
    ...
})
```

`source` uses `channelTitle` from the API (not generic "YouTube"), so `max_per_source` caps apply per channel.

## Prevention strategies

1. **Never use fallback data that hides errors.** If a data source fails, the section should be empty, not filled with hardcoded placeholders. Empty sections are immediately visible; fake data hides broken pipelines for months.

2. **Enforce hard age cutoffs at the API/fetch level**, not just soft scoring penalties. The 7-day `publishedAfter` parameter guarantees freshness before any scoring logic runs.

3. **Audit config for dead entries.** The 100 unused `youtube_search_queries` sat in config for weeks. Periodically grep config keys against the codebase to find entries nothing reads.

4. **Log source diversity metrics.** After scoring, log per-source article counts. Flag when <3 unique sources produce output — monoculture becomes visible in CI logs.

## Related documentation

- [Source concentration and display quality](../logic-errors/source-concentration-and-display-quality.md) — per-source caps, audience tuning
- [Uncommitted config after rewrite](../runtime-errors/uncommitted-config-after-rewrite.md) — config/code coupling gotcha
- [Product Hunt Atom feed integration](./producthunt-atom-feed-integration.md) — similar Atom parsing and per-source cap patterns
- [Cross-day article deduplication](../logic-errors/cross-day-article-deduplication.md) — dedup mechanism applies to YouTube URLs too
- Brainstorm: `docs/brainstorms/2026-02-23-youtube-search-api-brainstorm.md`
- Plan: `docs/plans/2026-02-23-feat-youtube-search-api-migration-plan.md`
