# YouTube Search API Migration

**Date:** 2026-02-23
**Status:** Ready for planning

## Problem

The current YouTube sourcing uses channel Atom feeds from 9 hardcoded channels. This causes:

1. **Rickroll/dead video bug** — Video ID `iN1Xx8ca_8I` (title: "LangChain Agent Executor Deep Dive") now shows Rick Astley. The original video was likely deleted/replaced on YouTube, but the feed entry persisted. No validation exists to catch this.
2. **Stale content** — Both videos in today's digest are from June 2025 (8 months old). No hard age cutoff exists — the recency score just floors at 0 but doesn't disqualify.
3. **LangChain monoculture** — Both videos are from James Briggs (lowest-reputation channel at 0.75), both LangChain-focused. The 7 higher-quality channels (Fireship, AI Jason, Cole Medin) produce nothing that passes the content filters.
4. **Dead config** — `youtube_search_queries` (100 queries) exists in config.json but is never used by fetcher.py.

## What We're Building

Replace channel-based YouTube fetching with YouTube Data API v3 search, using the existing 100 search queries in config.json.

### How it works

1. Each fetcher run picks **3 random queries** from `config.youtube_search_queries`
2. Calls YouTube Data API v3 search endpoint for each query (filtered to videos, sorted by relevance, published within window)
3. Applies existing content filters (`is_actionable_content`, `is_tool_content`)
4. Picks **top 3 videos** by score from the combined results
5. Age window: prefer 72 hours, **relax to 7 days** if nothing fresh enough

### What gets removed

- `config.sources.youtube_channels` — no longer needed
- `fetch_youtube_tutorials()` channel-based fetching in fetcher.py
- Channel Atom feed parsing for YouTube

### What gets added

- `YOUTUBE_API_KEY` env var (YouTube Data API v3 free tier)
- New `fetch_youtube_search()` function using the API
- Hard age cutoff (72h preferred, 7d fallback)
- API quota: ~300 units/day (3 searches x 100 units) out of 10,000 free limit

## Why This Approach

- **Diversity by design** — The 100 queries span cursor, claude, n8n, no-code, SaaS, automation, prompt engineering, etc. No single channel or topic can dominate.
- **Freshness guaranteed** — API search supports `publishedAfter` parameter, enforcing recency at the query level.
- **Already scoped** — The queries exist, the scoring/filtering pipeline exists. Only the fetch layer changes.
- **Simple rotation** — 3 random queries per run is stateless (no tracking file needed) and uses 3% of daily quota.

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| YouTube source method | API search (replace channels) | Channels were sparse and stale; search gives fresh, diverse results |
| Queries per run | 3 random | Low quota usage (300/10,000), good variety, stateless |
| Channel feeds | Remove entirely | Search replaces their function; simpler code |
| Empty state (no fresh videos) | Relax window to 7 days | Avoids empty sections while keeping content reasonably fresh |
| API key | New `YOUTUBE_API_KEY` env var | Required for Data API v3; free tier is generous |

## Open Questions

- Should we trim the 100 queries? Some overlap (e.g., "langchain agent tutorial" vs "ai agent tutorial langchain"). Could consolidate to ~50 distinct queries.
- Should we validate video liveness (e.g., check that the thumbnail isn't a default/missing image) to prevent future rickroll-type issues?
- Max videos per query result to consider? (YouTube API returns up to 50 per search, but we only need ~5 candidates per query.)
