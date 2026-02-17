# Cross-Day Article Deduplication

**Date:** 2026-02-17
**Status:** Ready for planning

## Problem

~32% of articles in the daily digest repeat from the previous day. The fetcher has no memory of what it showed before — each run starts completely fresh. RSS feeds keep items for days/weeks, so the same URLs get selected again.

The user's preference: **never show the same article twice, and show fewer articles rather than repeats.**

## What We're Building

A URL-based history system that prevents any article from appearing in the digest more than once within a 30-day window.

### How It Works

1. `fetcher.py` loads `data/seen_urls.json` at the start of each run
2. Articles are fetched and scored as usual
3. Any article whose URL is already in the history is excluded (hard block)
4. Selected articles have their URLs + today's date written to the history
5. Entries older than 30 days are pruned on each run
6. The history file is committed alongside `articles.json` by the existing CI workflow

### History File Format

```json
{
  "https://example.com/article-1": "2026-02-17",
  "https://example.com/article-2": "2026-02-16",
  ...
}
```

Simple URL → date-first-shown mapping. At ~50 URLs/day over 30 days, this stays under 1500 entries (~30KB).

## Why This Approach

- **URL matching is sufficient.** The duplication comes from the same feeds returning the same URLs — not from different URLs covering the same story.
- **No new dependencies.** Just stdlib JSON read/write, fits the project's zero-dependency philosophy.
- **Fits existing CI.** The GitHub Actions workflow already commits `data/`. The history file lives there too.
- **Easy to debug.** Open the JSON file, see exactly what's been shown and when.
- **Graceful degradation.** If the file is missing or corrupted, the fetcher just runs without dedup (no crash).

## Key Decisions

- **30-day dedup window** — long enough that repeats are extremely unlikely in practice
- **Hard block, not score penalty** — if it's been shown, it's out. No "reduce score by 50%" softness.
- **URL-only matching** — no content hashing or title similarity (YAGNI — URL dedup covers the actual problem)
- **No evergreen fallback** — on slow days, show fewer articles. Revisit if this becomes a real issue.
- **Storage in `data/seen_urls.json`** — committed to repo, travels with the codebase

## Open Questions

- Should the Vercel cron handler (`api/cron/fetch.py`) also use the same history? (It has its own inline fetcher logic.)
- Should there be a config toggle to disable dedup for local testing?

## Alternatives Considered

| Approach | Why not |
|---|---|
| Content hash dedup | More complex, URL matching already covers 95%+ of cases |
| Title similarity matching | Overkill — the duplication is exact URL repeats, not "same story different source" |
| Score penalty instead of hard block | User explicitly wants zero repeats, not fewer repeats |
| Evergreen content fallback | Deferred — solve the core problem first, add this later if needed |
