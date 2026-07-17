# News-focus pivot — design

Date: 2026-07-16
Status: approved (brainstorm), pending implementation plan

## Goal

Reframe AI Venture Digest from teaching people **how to use AI** to keeping them
**up to date with the latest AI news**. This is a full pivot, not a rebalance: the
tutorial / skill / how-to machinery is removed, and news becomes the product.

Audience is unchanged: vibe coders, marketers, solopreneurs, indie hackers (not
engineers). News is selected and framed for that audience, not for a technical one.

## Decisions locked in brainstorm

- **Full pivot** to news. Drop the actionable/teaching machinery entirely.
- **In-scope news:** model and feature releases, tool and product launches, funding
  and business moves, industry and strategy. Research breakthroughs only as written
  by accessible sources (not raw arxiv).
- **Out of scope:** drama and controversy (lawsuits, spats, "beef"), and
  roundups / other digests (a curated digest should not republish other digests).
- **Aggregation only.** No LLM summary layer. Items show the source's own headline
  and blurb. "Translated research" therefore comes from sources that already write
  accessibly, not from rewriting.
- **Ranking: reweight only.** No story clustering. The same story from multiple
  feeds may appear multiple times; dampened by the significance bonus and the
  per-source cap, but not eliminated. This is an accepted trade-off.
- **Structure: grouped by category** (four sections), not a lead-story treatment.

## Content model

### Categories

Every item is classified into exactly one category by keyword plus source-type
signals (same style as the existing content-type logic, retargeted).

| Category | Feeds from | Example signals |
|---|---|---|
| Releases | Labs and major apps | new Claude/GPT/Gemini models, "introducing", "now available", "GA", version bumps, major features |
| Launches | Third-party tools | Product Hunt, "new app/tool", "we built", "launched" |
| Business & Strategy | News feeds | "raises $", "acquires", partnerships, lab strategy moves, policy/regulation |
| Research | Accessible sources | "study", "benchmark", "breakthrough" as written by The Neuron / Ben's Bites |

Note: the original picks 3 (funding/business) and 4 (industry/strategy) are merged
into one "Business & Strategy" category to avoid thin sections on slow days.

### Gatekeeper: `is_newsworthy()` (replaces `is_actionable_content()`)

Inverts the current gatekeeper:

- Drops the requirement for how-to / tutorial keywords entirely.
- Welcomes what was previously hard-excluded: announcements, launches, funding,
  "introducing", "now available".
- Still hard-excludes: nature/wildlife noise, raw academic papers
  (arxiv / "variational autoencoder" / proofs), drama/controversy, and
  roundups / other digests.
- Still requires the item to be AI-related.

### Removed entirely

- Quick-wins / skill machinery: `select_rotated_skill`, skill rotation, and
  `create_quick_wins`.
- Note: `seen_urls` is **retained**. It is not just skill rotation; it drives
  cross-run dedup of all articles (fetcher.py:996-1002, 1075-1087) so the same
  story is not shown on consecutive days. This matters more, not less, for a news
  product. Only the skill-rotation *use* of it is removed.
- `github_skills` source and its `config.json` block.
- `is_tool_content`.
- `strict_actionable` flag.
- Tutorial-oriented `youtube_search_queries`.

## Ranking and sources

### Scoring reweight (`calculate_score` + `config.json.filters`)

| Factor | Now | Proposed | Rationale |
|---|---|---|---|
| Reputation | 0.25 | 0.30 | Source trust is the primary quality bar for news |
| Recency | 0.20 | 0.30 | News decays fast; today beats yesterday |
| Relevance | 0.30 | 0.20 | Still matters, less dominant than big + fresh |

- Important: `calculate_score` (fetcher.py:787-836) consumes **only**
  `reputation_weight`, `relevance_weight`, and `recency_weight`. The
  `engagement_weight` in config is dead (never referenced). Remove it from
  `config.json` rather than pretend to retune it (YAGNI). Scoring is these three
  weighted terms plus additive keyword bonuses; the weights do not need to sum to 1.
- Replace the tutorial `type_bonuses` dict and the `strong_actionable` bonus
  (fetcher.py:802-818) with a single **significance-keyword bonus** (+0.15 for
  "introducing", "now available", "generally available", "launches", "acquires",
  "raises", "partnership", "new model", "release"). This is the reweight-only
  substitute for corroboration.
- Tighten `max_age_hours` 72 -> 48. A news digest that leads with two-day-old items
  feels stale. Tunable; easy to revert.

### Sources

- **Drop:** `github_skills`.
- **Keep, retargeted:** RSS (already news-heavy: TechCrunch AI, The Verge AI,
  Ben's Bites, The Neuron), Product Hunt (feeds Launches), Twitter/Nitter
  (AnthropicAI / OpenAI announcements are prime Releases).
- **YouTube:** rewrite queries from tutorials to news recaps
  (e.g. "AI news this week", "new AI model announcement"). Weak news source, so
  give it a small quota and let it rank naturally low.
- **Podcasts:** discussion, not breaking news. Kept as a small "listen deeper"
  extra: the existing single `featured_podcast` spotlight is retained below the four
  news sections (`get_featured_podcast` / `is_podcast_relevant` stay).
- **Twitter/X:** the existing separate `twitter_posts` section is kept as-is,
  rendered after the four category sections. Tweets are not folded into the
  category taxonomy in this iteration.

## Output

### `articles.json` schema

- Remove the `quick_wins` block.
- Keep a single `articles` list; each item carries `category` (releases / launches /
  business / research). Frontend and email group by that field. No new nested
  schema.
- Retain the `featured_podcast` and `twitter_posts` fields unchanged; they continue
  to render as their own elements, not as category sections.

### `index.html`

The frontend is a fixed magazine layout with eight hardcoded sections (Quick Wins,
Featured Podcast, Must Reads, Videos, More Podcasts, Twitter, Launches, Quick Hits),
where `category` today only drives a badge colour, not section membership. The pivot
restructures the main article area into category sections while keeping the
non-category content sections.

- Remove the Quick Wins section (`#quickWinsSection` / `#quickWinsGrid`, index.html:1355)
  and its `renderQuickWins` logic + the `quick_wins` archive path (index.html:2105).
- Replace the single Must Reads section (`#mustReadsSection`, index.html:1396) with
  four category sections in fixed order: Releases -> Launches -> Business & Strategy
  -> Research, each built from `articles` filtered by `category`. Items with a
  `video_url` continue to route to the Videos section (existing behaviour), and
  `podcast` / `twitter` items keep their own sections, so only the four news
  category values land in the grid.
- Remove the standalone Product Hunt Launches section (`#launchesSection`,
  index.html:1467); Product Hunt items (category `launches`) now flow into the
  Launches category section.
- Keep as their own sections below the four category sections: Videos
  (`#videoSection`), More Podcasts (`#morePodcastsSection`), Twitter
  (`#twitterSection`), and the Featured Podcast spotlight (`#featuredPodcast`).
- Category sections with zero items for the day are hidden (no empty headers).
- Update `buildTOC()` and the scroll-spy section list to match the new section set
  (drop Quick Wins + standalone Launches, add the four category sections).
- Update the archive filter options (index.html:1531-1536) to the new categories.
- Preserve existing `escHtml()` / `safeUrl()` usage on all interpolation.

### `newsletter.py`

- It already groups by `category` (newsletter.py:46-66); there is no quick-wins
  email block to remove.
- Update the `category_info` map (newsletter.py:55-62) to the four new keys with
  news-framed titles and emojis. Remove the stale `tools` / `examples` entries, and
  render the four sections in fixed order.
- Replace the dead "TUTORIALS" stat (newsletter.py:159-163, counts
  `content_type == 'tutorial'`, now always 0) with a distinct-source count.
- Retag the teaching footer copy ("Curated with AI for venture builders") in both
  the HTML (newsletter.py:199) and plain-text (newsletter.py:246) versions to the
  new tagline.
- Group the plain-text version (`generate_newsletter_text`, newsletter.py:220-250)
  by the same four categories; today it renders a flat numbered list.
- The subject line (newsletter.py:361) already leads with the top story title; keep.
- Keep existing CTA / website-link and Outlook-fallback patterns.

### Shared category vocabulary (cross-file contract)

The fetcher currently assigns a loose mix of category values (`tutorial`, `tools`,
`deep_dive`, `podcast`, `skill`, `twitter`, `launch`) and the newsletter map only
partially matches them. The pivot standardises this. The category-assignment logic
in `fetcher.py` (the sites at 325-329, 549-556, 716-717, plus new classification)
must emit exactly the four values `releases` / `launches` / `business` / `research`,
and both `newsletter.py` `category_info` and the `index.html` section rendering must
key off those same four values. `twitter` and `podcast` remain as their own
non-category fields (Twitter section, featured-podcast spotlight), not category
values in the four-section grid.

### Copy / branding

- Product name unchanged: **AI Venture Digest**.
- Tagline: `"Actionable AI content for venture builders who ship"` ->
  `"The AI news that matters — for people who build."`
- Update section intros and empty-states to news language.

## Known trade-offs

- No clustering: duplicate coverage of the same story can appear as multiple
  entries. Accepted for this iteration. Clustering + a "top story" treatment is a
  natural follow-up if the duplicate noise proves annoying.
- Aggregation only: no plain-language rewriting. If "translated research" proves
  too technical in practice, an LLM summary layer is the designed follow-up phase.
