---
title: "feat: Replace YouTube channel feeds with Data API v3 search"
type: feat
date: 2026-02-23
---

# feat: Replace YouTube channel feeds with Data API v3 search

## Overview

Replace the broken channel Atom feed approach for YouTube videos with YouTube Data API v3 search, using ~25 curated search queries in `config.json`. This fixes stale content (8-month-old videos), rickroll/dead video issues, and LangChain monoculture — all caused by relying on channel RSS feeds that return sparse, unvalidated results.

## Problem Statement

The current `fetch_youtube_tutorials()` fetches Atom feeds from 9 hardcoded YouTube channels. Three compounding failures:

1. **Dead videos** — Video ID `iN1Xx8ca_8I` now redirects to Rick Astley. No liveness validation exists.
2. **Stale content** — Both videos in today's digest are from June 2025 (8 months old). No hard age cutoff — recency score floors at 0 but doesn't disqualify.
3. **Topic monoculture** — Only 2 of 9 channels produce content passing filters, both LangChain-focused from the lowest-reputation channel (James Briggs, 0.75).
4. **Dead config** — `youtube_search_queries` (100 queries) exists but is unused by the backend.

## Proposed Solution

New `fetch_youtube_search(config)` function that:

1. Reads `YOUTUBE_API_KEY` from env (graceful skip if missing)
2. Picks 3 random queries from `config.youtube_search_queries` (seeded by date for reproducible reruns)
3. Calls YouTube Data API v3 `search.list` for each query
4. On HTTP 403, breaks the query loop early (quota exhausted or key disabled)
5. Applies existing `is_actionable_content` / `is_tool_content` filters
6. Returns article dicts with the same schema as today

### API Call Parameters

```
GET https://www.googleapis.com/youtube/v3/search
  ?part=snippet
  &type=video
  &q={query}
  &maxResults=10
  &order=date
  &publishedAfter={7_days_ago_iso8601}
  &relevanceLanguage=en
  &key={YOUTUBE_API_KEY}
```

- `order=date` — get the freshest content and let our own filters be the editor, not YouTube's watch-time algorithm
- `publishedAfter=7d` — hard cutoff; the existing recency scoring naturally favors newer content within the window
- Quota: 3 queries x 100 units = 300 units/day (3% of 10,000 free tier)

### Article Dict Schema (unchanged contract)

```python
{
    'title': snippet['title'],
    'url': f"https://www.youtube.com/watch?v={video_id}",
    'description': snippet['description'][:300],
    'source': snippet['channelTitle'],      # channel name — required for per-source cap
    'reputation': 0.85,                      # below curated feeds (0.9-1.0) because we can't editorially vouch for unknown channels
    'published': snippet['publishedAt'],     # ISO 8601, already parsed by calculate_score()
    'thumbnail': f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
    'video_url': f"https://www.youtube.com/watch?v={video_id}",  # MUST be set — see note below
    'content_type': 'tutorial' or 'tool_demo',
    'podcast_duration': None,
    'fetched_at': datetime.utcnow().isoformat(),
    'category': 'tutorial' or 'tools',
    'score': 0  # calculated later by calculate_score()
}
```

Critical: `video_url` **must** be set (not `None`). The frontend uses `!a.video_url` to exclude videos from Must Reads (`index.html:1844`). Missing `video_url` = videos leak into Must Reads.

### Function Behavior

For each selected query:
- Call YouTube Data API v3 `search.list` with parameters above
- On HTTP 403, log the error and break the loop (quota exhausted or key revoked — don't waste remaining queries)
- On other errors, log and continue to next query
- For each result, apply `is_actionable_content` / `is_tool_content` filters (discard if neither passes)
- Build article dict matching schema above
- Return combined list from all queries

## Acceptance Criteria

- [x] YouTube videos in digest are fresh (< 7 days old)
- [x] Graceful degradation: missing API key or API failure = empty video section, no crash
- [x] `YOUTUBE_API_KEY` env var added to GitHub Actions workflow
- [x] Frontend rickroll default videos replaced with empty state
- [x] `video_url` field set on all YouTube articles (Must Reads exclusion works)
- [x] `youtube_search_queries` trimmed to ~25 distinct queries

## Implementation Tasks

### 1. Replace `fetch_youtube_tutorials()` with `fetch_youtube_search()` and update config

**Files:** `scripts/fetcher.py`, `config.json`

- Delete `fetch_youtube_tutorials()` (lines 249-294)
- Write new `fetch_youtube_search(config)` following the spec above
- Update call site in `main()` (~line 764): `fetch_youtube_tutorials(config)` → `fetch_youtube_search(config)`
- Add `import random` at top of file (`urllib.parse` already imported)
- Use `random.seed(datetime.utcnow().strftime('%Y-%m-%d'))` for deterministic daily selection (reproducible CI reruns)
- Remove `sources.youtube_channels` array from `config.json` (lines 30-40)
- Trim `youtube_search_queries` from 100 to ~25 distinct queries — cut duplicates:
  - 10 "claude code \*" variants → keep 3 ("claude code tutorial", "claude code workflow tips", "claude code project setup")
  - 8 "cursor ai \*" variants → keep 3 ("cursor ai tutorial build app", "cursor ai vs copilot", "cursor ai advanced tips")
  - 9 "langchain \*" variants → keep 2 ("langchain agent tutorial", "langchain RAG tutorial")
  - 7 generic "build ai \* tutorial" fillers → keep 2 ("build ai app no code", "build ai saas tutorial")
  - Keep all unique topic queries (n8n, prompt engineering, voice AI, etc.)

**Note:** The `fetch_rss` YouTube URL branch (lines 210-215) becomes dead code for YouTube content. It's still exercised by RSS feeds that link to YouTube videos, so leave it in place.

### 2. Add `YOUTUBE_API_KEY` to GitHub Actions workflow

**File:** `.github/workflows/daily-fetch.yml`

```yaml
- name: Run fetcher
  env:
    YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
  run: python scripts/fetcher.py
```

### 3. Replace frontend rickroll defaults with empty state

**File:** `index.html`, lines ~1919-1928

Replace the hardcoded `dQw4w9WgXcQ` fallback videos with a "No fresh tutorials today" empty state. This must ship in the same commit as the fetcher change — otherwise API failure triggers the same rickroll bug we're fixing.

## Gotchas

| Gotcha | Prevention |
|---|---|
| Config + code must ship in same commit | Stage `config.json`, `fetcher.py`, `index.html`, and workflow changes together |
| `video_url` must be truthy | Set it explicitly; `None` breaks Must Reads exclusion (`index.html:1844`) |
| Per-source cap uses `source` field | Use `channelTitle` from API (not generic "YouTube"), so `max_per_source: 2` applies per channel |

## Dependencies

- Google Cloud project with YouTube Data API v3 enabled (free)
- `YOUTUBE_API_KEY` added as GitHub Actions secret
- Restrict the API key in Google Cloud Console to YouTube Data API v3 only

## Post-Deploy Verification

After adding the secret, trigger a manual workflow run to verify:

```bash
gh workflow run "Daily AI Digest Fetch"
```

Check that `data/articles.json` contains video entries with valid YouTube URLs, fresh dates, and diverse channels.

## Out of Scope

- Updating `api/cron/fetch.py` (Vercel cron) — separate codebase, doesn't fetch YouTube. Note: the Vercel cron also produces an incompatible article dict schema (`summary` vs `description`, `publishedAt` vs `published`, missing `video_url`/`thumbnail`/`content_type`). It would need its own migration if it becomes the primary trigger.
- Video liveness validation — API only returns published, live videos
- Quota monitoring/alerting — comfortable margin at 3% of daily limit

## References

- Brainstorm: `docs/brainstorms/2026-02-23-youtube-search-api-brainstorm.md`
- Current fetch function: `scripts/fetcher.py:249-294`
- Frontend video rendering: `index.html:1910-1951`
- GitHub Actions workflow: `.github/workflows/daily-fetch.yml`
- Documented learning (config coupling): `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md`
- Documented learning (source diversity): `docs/solutions/logic-errors/source-concentration-and-display-quality.md`
- YouTube Data API v3 docs: https://developers.google.com/youtube/v3/docs/search/list
