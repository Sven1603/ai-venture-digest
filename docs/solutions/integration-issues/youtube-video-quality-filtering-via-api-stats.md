---
title: "YouTube video quality filtering via API statistics — flat reputation, low-quality videos surfacing"
category: integration-issues
module: scripts/fetcher.py, config.json
tags: [youtube, data-api, content-quality, video-stats, channel-stats, graceful-degradation]
symptoms:
  - "3-view video from 10-subscriber channel scores identically to 100K-view video from major creator"
  - "All YouTube videos receive flat 0.85 reputation regardless of channel or video quality"
  - "Low-quality YouTube content regularly surfaces in digest alongside premium creators"
root_cause: "YouTube search.list returns results without quality signals — all videos get a flat 0.85 reputation score with no view count or channel size differentiation"
date_solved: 2026-03-03
severity: medium
related:
  - docs/solutions/integration-issues/youtube-channel-feed-to-search-api-migration.md
  - docs/solutions/logic-errors/source-concentration-and-display-quality.md
  - docs/solutions/security-issues/xss-and-code-review-hardening.md
---

# YouTube video quality filtering via API statistics

## Problem

After migrating to YouTube Data API v3 `search.list` (see related migration doc), all YouTube videos received a flat `0.85` reputation score regardless of actual quality. A 3-view video from a 10-subscriber channel scored identically to a 100K-view video from a major creator. This regularly surfaced low-quality content to readers.

The `search.list` endpoint returns snippet data (title, description, channel name) but no statistics. Quality signals require separate API calls.

## Root Cause

The `search.list` API only returns `snippet` data. View counts, like counts, and subscriber counts live in separate endpoints (`videos.list` and `channels.list` with `part=statistics`). Without fetching these, there was no way to distinguish video quality.

The existing scoring system (`calculate_score()`) uses `reputation_weight` (25%), but reputation is set per-source in `config.json`, not per-video. YouTube as a source gets 0.85 across the board.

## Solution

### 1. Two additional batched API calls after `search.list`

Added `_fetch_video_statistics()` and `_fetch_channel_statistics()` to make batched calls:

```python
# videos.list — gets viewCount, likeCount per video (1 quota unit for up to 50 IDs)
_fetch_video_statistics(api_key, video_ids)

# channels.list — gets subscriberCount, hiddenSubscriberCount per channel (1 quota unit)
_fetch_channel_statistics(api_key, channel_ids)
```

Quota impact: +2 units/day on a 10,000/day free tier — negligible.

### 2. Hard gate filter (AND logic)

Videos are only dropped when **both** conditions fail:
- Channel has < 1,000 subscribers **AND**
- Video has < 500 views

A viral video (50K views) from a small channel (800 subs) passes. A new video (200 views) from a large channel (50K subs) also passes. Only genuinely low-quality content (small channel AND low views) gets filtered.

```python
passes_views = (video_stats is None) or (views >= min_views)
passes_subs = (channel_stats is None) or (subs >= min_subs) or hidden_subs

if not passes_views and not passes_subs:
    # Drop — both gates failed
    continue
```

### 3. Config-driven thresholds

```json
"filters": {
    "youtube_min_views": 500,
    "youtube_min_subscribers": 1000
}
```

Flat keys in the existing `filters` block, matching the pattern of `max_per_source` and `max_articles`. Tunable without code changes.

### 4. Temporary field pattern for internal data

`video_id` and `channel_id` are stored on article dicts during processing, then `pop()`'d before returning from `fetch_youtube_search()`:

```python
# During search — store for stats lookup
'video_id': video_id,
'channel_id': snippet.get('channelId', ''),

# After stats filtering — clean up before return
for v in videos:
    v.pop('video_id', None)
    v.pop('channel_id', None)
```

This keeps internal fields from leaking into `articles.json` or downstream consumers.

## Key Patterns

### Graceful degradation via None vs {} return convention

The stats helper functions use a three-state return to distinguish API failure from empty results:

| Return | Meaning | Effect on gate |
|--------|---------|----------------|
| `None` | API call failed | Gate is skipped entirely |
| `{}` | Success, no results | Gate applies (data is authoritative) |
| `{id: stats}` | Normal success | Gate applies with real data |

This prevents zeroed-out data from a failed API call from falsely filtering good videos:

```python
# If videos.list failed (None), skip view gate — don't apply with zero data
passes_views = (video_stats is None) or (views >= min_views)
```

### Safe int casting for external API data

YouTube API returns numeric values as strings (`"12345"`). A `_safe_int()` helper wraps the `int()` cast:

```python
def _safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default
```

Without this, a malformed stat value (`None`, empty string, non-numeric) would crash the entire YouTube section for that day.

### API key protection in error handlers

Generic `except Exception` handlers must NOT interpolate the exception object (`{e}`), because `urllib` exceptions can include the full URL — which contains the API key as a query parameter. Use endpoint-specific messages instead:

```python
# WRONG — can leak API key in CI logs
except Exception as e:
    print(f"  ⚠ YouTube videos.list failed: {e}")

# RIGHT — safe for CI logs
except Exception:
    print("  ⚠ YouTube videos.list failed unexpectedly")
```

This was a regression caught during code review — the existing `fetch_youtube_search` handler (line 309) had already been fixed in PR #10.

## What Was Intentionally Deferred (v2)

- **Engagement scoring** (likes/views ratio into `engagement_weight`) — the hard gate does 95% of the quality work. Engagement scoring adds marginal differentiation among survivors and would require resolving the neutral baseline problem: non-YouTube articles lack engagement data, so a flat 0.5 default would bias scoring.
- **Fresh video exemption** — a daily digest doesn't need real-time freshness exceptions. A video too new to have 500 views will surface tomorrow.

## Prevention

1. **Always use `_safe_int()` for external API numeric data** — never bare `int()` on values from HTTP responses
2. **Never log `{e}` in handlers for functions that construct URLs with secrets** — use endpoint-specific messages
3. **Use the None vs {} convention** when a function needs to distinguish "call failed" from "call succeeded with no results"
4. **Pop temporary fields before returning** when internal data is stored on shared dicts — prevents schema leakage to downstream consumers
5. **Config thresholds over hardcoded values** — flat keys in the `filters` block, following existing patterns

## Files Changed

- `scripts/fetcher.py` — `_safe_int()`, `_fetch_video_statistics()`, `_fetch_channel_statistics()`, `fetch_youtube_stats()`, wiring in `fetch_youtube_search()`
- `config.json` — `youtube_min_views`, `youtube_min_subscribers` in `filters` block

## References

- PR #11: feat(youtube): add video quality filtering via API statistics
- Brainstorm: `docs/brainstorms/2026-03-03-youtube-video-quality-filtering-brainstorm.md`
- Plan: `docs/plans/2026-03-03-feat-youtube-video-quality-filtering-plan.md`
- Prior YouTube migration: `docs/solutions/integration-issues/youtube-channel-feed-to-search-api-migration.md`
- XSS/security hardening (API key redaction origin): `docs/solutions/security-issues/xss-and-code-review-hardening.md`
