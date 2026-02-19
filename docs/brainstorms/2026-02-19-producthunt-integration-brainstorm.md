# Brainstorm: Product Hunt AI Tool Launches

**Date:** 2026-02-19
**Status:** Ready for planning

## What We're Building

Add Product Hunt as a new content source to surface practical AI productivity tools that readers can start using immediately. Launches appear in a distinct "Product Launches" section with their own badge and emoji, giving them visibility without blending into existing tool articles.

## Why This Approach

- **RSS feed** — no API key, no new dependencies, reuses existing `fetch_rss()` helper
- **AI keyword filter** — keeps content on-topic for the target audience (vibe coders, solopreneurs, indie hackers)
- **Distinct category** — readers can quickly spot new AI product launches in both the newsletter and website
- **Consistent with architecture** — follows the same pattern as every other source type (config entry, fetch function, content filter, scoring)

## Key Decisions

1. **Data source:** Product Hunt RSS feed (no API key needed)
2. **Filtering:** AI/productivity keyword filter to keep launches relevant
3. **Display:** Own category (`launch`) with distinct badge and emoji in newsletter + website
4. **Content type:** `product_launch` — will need a scoring bonus in `calculate_score()`
5. **Volume:** Governed by existing `max_per_source: 3` cap

## Touch Points

1. `config.json` — add `producthunt` source entry with feed URL and reputation score
2. `scripts/fetcher.py` — add `fetch_producthunt()` function, call from `main()`, add `product_launch` to type bonuses
3. `index.html` — add CSS badge style and emoji for `launch` category
4. `scripts/newsletter.py` — ensure new category renders properly (may need section header)

## Open Questions

- What reputation score for Product Hunt? (Suggest 0.85 — good signal but unvetted individual launches)
- What AI keywords to filter on? (Starting set: AI, artificial intelligence, GPT, LLM, automation, no-code, copilot, agent, chatbot, machine learning, productivity, workflow)
- What emoji for the launch badge? (Suggest: rocket emoji)
- What scoring bonus for `product_launch`? (Suggest 0.12 — on par with podcasts, below tutorials)
