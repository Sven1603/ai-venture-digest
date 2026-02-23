---
title: "Stored XSS via innerHTML interpolation and code review hardening across YouTube API migration"
category: security-issues
module: index.html, scripts/fetcher.py
tags: [xss, security, innerHTML, html-escaping, code-review, random-state, deduplication, single-source-of-truth]
symptoms:
  - "All 9 render functions in index.html interpolate article data into innerHTML without escaping"
  - "Global random.seed() pollutes state for all subsequent random calls in the process"
  - "Duplicate video IDs possible across multiple YouTube search queries"
  - "Frontend hardcodes 25 YouTube search queries duplicating config.json (single-source-of-truth violation)"
  - "datetime.utcnow() deprecated in Python 3.12+"
  - "Generic exception handler leaks API key in error message"
root_cause: "YouTube API migration (PR #10) introduced new data paths from untrusted external sources (YouTube API) directly into innerHTML without sanitization; supporting code used deprecated APIs and patterns that could cause subtle bugs"
date_solved: 2026-02-23
severity: high
---

# Stored XSS and code review hardening

## Problem

After merging PR #10 (YouTube channel feeds → Data API v3 search), a multi-agent code review identified 10 findings across `index.html` and `scripts/fetcher.py`. Two were P1 (critical):

1. **Stored XSS via innerHTML** — All 9 render functions (`renderQuickWins`, `renderFeaturedPodcast`, `renderMustReads`, `renderVideos`, `renderTwitterPosts`, `renderMorePodcasts`, `renderLaunches`, `renderMoreUpdates`, archive render) interpolated untrusted data (`title`, `description`, `source`, `url`) directly into `innerHTML` template literals without escaping. An attacker who controls any content source (RSS feed, YouTube API response, Twitter post) could inject arbitrary HTML/JS.

2. **URL injection** — `href` attributes constructed from article URLs without protocol validation. A `javascript:` URL in a feed entry would execute on click.

Eight additional P2/P3 findings:

3. Global `random.seed()` pollutes state for the entire process
4. No deduplication — same video appearing in multiple query results
5. Frontend hardcoded 25 search queries duplicating `config.json`
6. `datetime.utcnow()` deprecated since Python 3.12
7. Unnecessary dict fields (`score: 0`, `podcast_duration: None`)
8. No video ID format validation (injection via crafted `videoId`)
9. User-Agent string inconsistent with rest of codebase
10. Generic `except` handler could leak API key in error messages

## Root Causes

**No HTML escaping layer existed.** The frontend was built assuming trusted data, but every content source (RSS feeds, YouTube API, Twitter/Nitter, Hacker News, Reddit) returns user-generated content that can contain HTML special characters or malicious payloads.

**URL construction assumed valid URLs.** Links were built from feed data without verifying the protocol, allowing `javascript:`, `data:`, or other dangerous schemes.

**Initial implementation prioritized correctness over defense-in-depth.** The YouTube API migration focused on fixing stale content and topic monoculture. Security hardening was deferred to review.

## Solution

### 1. XSS prevention — `escHtml()` and `safeUrl()` helpers (`index.html`)

Added two sanitization functions:

```javascript
function escHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function safeUrl(url) {
    if (!url) return '#';
    try {
        const u = new URL(url);
        return (u.protocol === 'https:' || u.protocol === 'http:') ? url : '#';
    } catch { return '#'; }
}
```

Applied across all 9 render functions:
- **Text content** (`title`, `description`, `source`, `label`, `category`, `author`) → `escHtml()`
- **`href` attributes** (`url`, `video_url`) → `safeUrl()`
- **`src` attributes** (thumbnails) → `safeUrl()`
- **`alt` attributes** → `escHtml()`
- **CSS class interpolation** (`category` badge) → `escHtml()`

### 2. Isolated random state (`fetcher.py`)

Replaced global `random.seed()` with instance-scoped `random.Random()`:

```python
# Before — pollutes global state
random.seed(datetime.utcnow().strftime('%Y-%m-%d'))
selected = random.sample(queries, min(3, len(queries)))

# After — isolated instance
rng = random.Random(datetime.now(timezone.utc).strftime('%Y-%m-%d'))
selected = rng.sample(queries, min(3, len(queries)))
```

### 3. Video deduplication (`fetcher.py`)

Added `seen_ids` set to prevent duplicate videos across queries:

```python
seen_ids = set()
# ... inside loop:
if video_id in seen_ids:
    continue
seen_ids.add(video_id)
```

### 4. Single source of truth for search queries (`fetcher.py` + `index.html`)

Eliminated the duplicated 25-query list from `index.html`. The fetcher now passes `youtube_search_queries` from config through `data/articles.json`:

```python
# fetcher.py — main() output dict
'youtube_search_queries': config.get('youtube_search_queries', []),
```

```javascript
// index.html — loadArticles()
youtubeSearchQueries = data.youtube_search_queries || [];

// getDailyYouTubeSearchQuery() — reads from loaded data
const queries = youtubeSearchQueries.length > 0 ? youtubeSearchQueries : ['ai tutorial'];
```

### 5. Deprecated datetime fix (`fetcher.py`)

```python
# Before (deprecated in 3.12)
datetime.utcnow()

# After
datetime.now(timezone.utc)
```

### 6. Video ID validation (`fetcher.py`)

```python
VIDEO_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,20}$')

# In fetch loop:
if not video_id or not VIDEO_ID_RE.match(video_id):
    continue
```

### 7. API key redaction in error messages (`fetcher.py`)

```python
# Before — could leak key in logs
except Exception as e:
    print(f"  ⚠ YouTube search failed: {e}")

# After — no exception details
except Exception as e:
    print(f"  ⚠ YouTube search failed for query '{query}'")
```

### 8. Minor cleanup (`fetcher.py`)

- Removed `'score': 0` and `'podcast_duration': None` — both set downstream by `calculate_score()` and unused by consumers
- Updated User-Agent to `Mozilla/5.0 AI-Venture-Digest/2.0` matching codebase convention

## Prevention strategies

1. **Treat all external data as untrusted.** Any value from RSS, APIs, or scrapers must be escaped before `innerHTML` interpolation. The `escHtml()` / `safeUrl()` pattern should be applied to any new render function.

2. **Never use global `random.seed()` in long-running processes.** Use `random.Random(seed)` instances to avoid polluting state for unrelated code.

3. **Pass config through the data pipeline, not hardcoded in consumers.** If the frontend needs config values, the fetcher should include them in `data/articles.json`. This prevents config/frontend drift.

4. **Redact secrets in error handlers.** Generic `except` blocks that log `{e}` can leak API keys, tokens, or URLs containing credentials. Log the operation context, not the exception object.

5. **Run multi-agent code review on security-sensitive changes.** The YouTube API migration introduced a new external data source — exactly the kind of change that warrants automated security review before merge.

## Related documentation

- [YouTube channel feed to search API migration](./youtube-channel-feed-to-search-api-migration.md) — the migration that introduced these data paths
- [Source concentration and display quality](../logic-errors/source-concentration-and-display-quality.md) — per-source caps, audience tuning
- [Uncommitted config after rewrite](../runtime-errors/uncommitted-config-after-rewrite.md) — config/code coupling gotcha
