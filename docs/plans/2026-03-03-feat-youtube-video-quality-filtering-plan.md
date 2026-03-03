---
title: "feat: YouTube video quality filtering via API statistics"
type: feat
date: 2026-03-03
---

# feat: YouTube video quality filtering via API statistics

## Overview

Add video and channel quality signals to YouTube curation by fetching statistics from the YouTube Data API v3. Videos below quality thresholds are dropped. No changes to the scoring system — the hard gate alone solves the core problem.

## Problem Statement

All YouTube videos receive a flat `0.85` reputation score regardless of channel or video quality. A 3-view video from a 10-subscriber channel scores identically to a 100K-view video from a major creator. This regularly surfaces low-quality content to readers.

## Proposed Solution

After the existing `search.list` call returns video IDs, make two additional **batched** API calls:

1. **`videos.list`** with `part=statistics` — gets `viewCount`, `likeCount` per video
2. **`channels.list`** with `part=statistics` — gets `subscriberCount`, `hiddenSubscriberCount` per channel

Then apply:
- **Hard gate:** Drop videos where channel has <1,000 subscribers **AND** video has <500 views (both must fail to be dropped)
- **Graceful degradation:** If either API call fails, skip that gate entirely

### What's intentionally deferred (v2)

- **Engagement scoring** (likes/views ratio into `engagement_weight`) — the hard gate does 95% of the quality work. Engagement scoring adds marginal differentiation among survivors and would require resolving the neutral baseline problem for non-YouTube articles. Defer until we observe quality problems among videos that pass the hard gate.
- **Fresh video exemption** — a daily digest doesn't need real-time freshness exceptions. A video that's too new to have 500 views will surface tomorrow.

### Quota Impact

| API Call | Cost | Current | New |
|----------|------|---------|-----|
| `search.list` (×3) | 100/call | 300 | 300 |
| `videos.list` (≤50 IDs batched) | 1/call | 0 | 1 |
| `channels.list` (≤50 IDs batched) | 1/call | 0 | 1 |
| **Total** | | **300** | **302** |

Negligible: +2 units on a 10,000/day free tier.

## Technical Approach

### Files Modified

| File | Change |
|------|--------|
| `scripts/fetcher.py` | Add stats fetching and hard gate filtering |
| `config.json` | Add `youtube_min_views`, `youtube_min_subscribers` to `filters` |

No changes to `index.html`, `newsletter.py`, `calculate_score()`, or CI workflow. The `YOUTUBE_API_KEY` already has access to `videos.list` and `channels.list`.

### Implementation Steps

#### Step 1: Add config thresholds to `config.json`

Add flat keys to the existing `filters` block (matching the pattern of `max_per_source`, `max_articles`):

```json
"youtube_min_views": 500,
"youtube_min_subscribers": 1000
```

No nested `youtube_quality` object — keep it flat and consistent.

Note: these thresholds use AND logic — a video is only dropped if it fails **both**. A viral video (50K views) from a small channel (800 subs) passes. A new video (200 views) from a large channel (50K subs) also passes.

#### Step 2: Store `channelId` during search (modify `fetch_youtube_search`)

The `search.list` response already includes `snippet.channelId`. Store it on each article dict so `fetch_youtube_stats()` can batch-fetch channel statistics without an extra API call.

In `fetch_youtube_search()`, around line 327 (article dict construction), add:

```python
'channel_id': snippet.get('channelId', ''),
```

This field gets `pop()`'d before writing to `articles.json` (in Step 5).

#### Step 3: Add `_fetch_video_statistics()` and `_fetch_channel_statistics()` helpers

Two small functions following the existing API call pattern in `fetch_youtube_search()`:

```python
def _fetch_video_statistics(api_key, video_ids):
    """Batch fetch video statistics. Returns dict {video_id: stats} or None on failure."""
    if not video_ids:
        return {}
    params = urllib.parse.urlencode({
        'part': 'statistics',
        'id': ','.join(video_ids[:50]),  # API max 50 per call
        'key': api_key,
    })
    url = f"https://www.googleapis.com/youtube/v3/videos?{params}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 AI-Venture-Digest/2.0'
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8', errors='ignore'))
        return {item['id']: item.get('statistics', {}) for item in data.get('items', [])}
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("  ⚠ YouTube API quota exhausted on videos.list (403)")
        else:
            print(f"  ⚠ YouTube videos.list error ({e.code}): {e.reason}")
        return None
    except Exception as e:
        print(f"  ⚠ YouTube videos.list failed: {e}")
        return None


def _fetch_channel_statistics(api_key, channel_ids):
    """Batch fetch channel statistics. Returns dict {channel_id: stats} or None on failure."""
    if not channel_ids:
        return {}
    params = urllib.parse.urlencode({
        'part': 'statistics',
        'id': ','.join(channel_ids[:50]),  # API max 50 per call
        'key': api_key,
    })
    url = f"https://www.googleapis.com/youtube/v3/channels?{params}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 AI-Venture-Digest/2.0'
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8', errors='ignore'))
        result = {}
        for item in data.get('items', []):
            stats = item.get('statistics', {})
            stats['hiddenSubscriberCount'] = item.get('statistics', {}).get('hiddenSubscriberCount', False)
            result[item['id']] = stats
        return result
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("  ⚠ YouTube API quota exhausted on channels.list (403)")
        else:
            print(f"  ⚠ YouTube channels.list error ({e.code}): {e.reason}")
        return None
    except Exception as e:
        print(f"  ⚠ YouTube channels.list failed: {e}")
        return None
```

#### Step 4: Add `fetch_youtube_stats()` orchestrator in `fetcher.py`

New function placed after `fetch_youtube_search()` (~line 344). Takes a list of video dicts, returns the filtered list.

```python
def fetch_youtube_stats(videos, config):
    """
    Fetch YouTube video/channel statistics and filter by quality thresholds.
    If stats API calls fail, returns videos unfiltered (graceful degradation).
    """
    api_key = os.environ.get('YOUTUBE_API_KEY', '')
    if not api_key or not videos:
        return videos

    filters = config['filters']
    min_views = filters.get('youtube_min_views', 500)
    min_subs = filters.get('youtube_min_subscribers', 1000)

    # Extract video IDs and unique channel IDs from search results
    video_ids = [extract_video_id(v['url']) for v in videos]
    channel_ids = list({v.get('channel_id') for v in videos if v.get('channel_id')})

    # Batch fetch statistics
    video_stats = _fetch_video_statistics(api_key, video_ids)
    channel_stats = _fetch_channel_statistics(api_key, channel_ids)

    # If both API calls failed, return videos unfiltered
    if video_stats is None and channel_stats is None:
        return videos

    # Apply hard gates
    filtered = []
    for v in videos:
        vid = extract_video_id(v['url'])
        cid = v.get('channel_id', '')

        # If a video is missing from stats response (deleted/private), skip it
        # If the API call itself failed (None), skip that gate entirely
        if video_stats is not None and vid not in video_stats:
            print(f"    ✗ Skipped (not in stats): {v['title'][:60]}")
            continue

        vs = video_stats.get(vid, {}) if video_stats else {}
        cs = channel_stats.get(cid, {}) if channel_stats else {}

        views = int(vs.get('viewCount', '0'))
        subs = int(cs.get('subscriberCount', '0'))
        hidden_subs = cs.get('hiddenSubscriberCount', False)

        # Hard gate: both must fail to be dropped
        # If an API call failed (None), that gate is automatically passed
        passes_views = (video_stats is None) or (views >= min_views)
        passes_subs = (channel_stats is None) or (subs >= min_subs) or hidden_subs

        if not passes_views and not passes_subs:
            print(f"    ✗ Filtered: {v['title'][:60]} (views={views}, subs={subs})")
            continue

        filtered.append(v)

    dropped = len(videos) - len(filtered)
    if dropped:
        print(f"  ℹ Filtered {dropped}/{len(videos)} videos below quality thresholds")

    return filtered
```

**Key design decisions:**
- **Partial API failure:** If `channels.list` fails but `videos.list` succeeds, only the view gate applies (subscriber gate is skipped). And vice versa. A video is never penalized by zeroed data from a failed API call.
- **Missing from stats response:** If a video ID exists in `video_stats` dict but is absent (deleted/private between search and stats call), it's skipped. This is distinct from the API call failing entirely.
- **`hiddenSubscriberCount: true`:** Bypasses the subscriber gate. We can't evaluate what we can't see, so we fall back to the view gate alone.
- **No engagement scoring:** Views, subs, likes are used as local variables only — nothing stored on the article dict except `channel_id` (which gets removed). No changes to `calculate_score()`.
- **Division by zero:** Not applicable — we only compare integers against thresholds, no ratios computed.
- **API returns strings:** Explicit `int()` cast on `viewCount` and `subscriberCount`.

#### Step 5: Wire into `fetch_youtube_search` and clean up `channel_id`

At the end of `fetch_youtube_search()` (around line 341), before `return videos`:

```python
# Enrich with statistics and apply quality filter
videos = fetch_youtube_stats(videos, config)

# Remove internal channel_id field (not needed downstream)
for v in videos:
    v.pop('channel_id', None)
```

This keeps everything inside the YouTube fetch path — `main()` doesn't change at all.

### Pipeline Position

```
fetch_youtube_search()
  └─ search.list API call (existing)
  └─ content filtering (existing: is_actionable_content, is_tool_content)
  └─ fetch_youtube_stats() ← NEW (stats fetch + hard gate)
  └─ pop('channel_id') ← NEW (cleanup)
  └─ return filtered videos

main()
  └─ all_articles = videos + podcasts + blogs + ...  (unchanged)
  └─ calculate_score()                                (unchanged)
  └─ dedup against seen_urls.json                     (unchanged)
  └─ source diversity cap                             (unchanged)
  └─ write articles.json                              (unchanged)
```

### New helper: `extract_video_id()`

The function needs to parse `https://www.youtube.com/watch?v=XXXX` back to `XXXX`. Place it near the existing `VIDEO_ID_RE` regex (line 250):

```python
def extract_video_id(url):
    """Extract video ID from YouTube URL. Returns empty string on failure."""
    parsed = urllib.parse.urlparse(url)
    video_id = urllib.parse.parse_qs(parsed.query).get('v', [''])[0]
    if VIDEO_ID_RE.match(video_id):
        return video_id
    return ''
```

## Acceptance Criteria

- [x] Videos with <500 views AND <1,000 channel subscribers are dropped
- [x] Channels with hidden subscriber counts bypass the subscriber threshold
- [x] If `videos.list` fails, the view gate is skipped (not applied with zero data)
- [x] If `channels.list` fails, the subscriber gate is skipped (not applied with zero data)
- [x] If both API calls fail, all videos pass through unfiltered
- [x] Videos missing from the stats response (deleted/private) are skipped
- [x] Stats API failure does not crash the pipeline
- [x] API statistics strings are cast to `int()`
- [x] Filtered videos are logged with title, views, and subscriber count
- [x] `channel_id` is removed from article dicts before returning from `fetch_youtube_search()`
- [x] `config.json` gains `youtube_min_views` and `youtube_min_subscribers` in `filters`
- [x] `calculate_score()` is NOT modified — `engagement_weight` stays dead (deferred to v2)
- [x] Total API quota stays under 305 units/day

## Edge Cases

| Case | Behavior |
|------|----------|
| `videos.list` returns 403 (quota) | Log warning, skip view gate — only subscriber gate applies |
| `channels.list` fails, `videos.list` succeeds | Apply view threshold only, skip subscriber gate |
| Both API calls fail | Return all videos unfiltered (graceful degradation) |
| `hiddenSubscriberCount: true` | Bypass subscriber threshold — fall back to view gate alone |
| Video missing from stats response | Skipped (likely deleted/private between search and stats call) |

## Config Changes

```json
"youtube_min_views": 500,
"youtube_min_subscribers": 1000
```

Added as flat keys in the `filters` block. No new environment variables. No CI workflow changes.

## Future (v2) — Engagement Scoring

If the hard gate proves insufficient and quality problems persist among surviving videos, consider:
- Fetching `likeCount` and computing engagement ratio (`likes/views`)
- Activating the dead `engagement_weight: 0.25` in `calculate_score()`
- Resolving the neutral baseline problem for non-YouTube articles (apply weight only when `engagement` key is present, not a flat 0.5)
- Handling disabled likes (absent `likeCount`) as neutral, not zero

## References

- Brainstorm: `docs/brainstorms/2026-03-03-youtube-video-quality-filtering-brainstorm.md`
- Current fetch function: `scripts/fetcher.py:253-343`
- Dead engagement_weight: `config.json:83` (stays dead — deferred to v2)
- YouTube API migration doc: `docs/solutions/integration-issues/youtube-channel-feed-to-search-api-migration.md`
- Source concentration learnings: `docs/solutions/logic-errors/source-concentration-and-display-quality.md`
- Config dead code learnings: `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md`
