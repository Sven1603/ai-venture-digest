---
title: "feat: Skill rotation and curated list cleanup"
type: feat
date: 2026-03-05
brainstorm: docs/brainstorms/2026-03-05-skill-rotation-and-discovery-brainstorm.md
---

# feat: Skill rotation and curated list cleanup

## Overview

The daily "Claude Skill" quick win always shows obra/superpowers because `create_quick_wins()` hardcodes `skills[0]`. Fix this with: (1) a rotation function using `seen_urls` history, and (2) replacing the fake gist URLs in config with real, curated skill repos.

## Problem Statement

- `scripts/fetcher.py:868` — always picks `skills[0]`, zero rotation
- `config.json:37-52` — 14 static entries, 11 of which are placeholder gist URLs that don't exist
- Readers see the same skill every day, reducing the value of the quick wins section

## Proposed Solution

### 1. Rotation via `select_rotated_skill()`

Add a function that picks a skill the reader hasn't seen recently.

**Algorithm:**
1. Take full skill pool + `seen_urls` dict + today's date string
2. Build set of "recently shown" skill URLs: intersection of `seen_urls` keys and skill pool URLs (avoids confusing skill URLs with tool/article URLs)
3. Filter pool to skills NOT in recently-shown set
4. If pool is empty (all shown within 30-day window), sort all skills by `seen_urls[url]` date ascending, pick from oldest
5. Use date-seeded `random.Random(date_str)` to pick deterministically (same skill on re-runs within a day — matches YouTube pattern at `fetcher.py:275-277`)

**Code changes:**
- `scripts/fetcher.py` — new `select_rotated_skill(skills, seen, today)` function (~15 lines)
- `scripts/fetcher.py:868` — replace `skill = skills[0]` with `skill = select_rotated_skill(skills, seen, today)`
- `scripts/fetcher.py:986` — remove the skill dedup exemption (`content_type == 'skill'`). Skills no longer need to bypass dedup because rotation handles selection independently before the main dedup pass.

### 2. Curate the skill list

Replace the placeholder gist URLs in `config.json` `github_skills` with 20-30 real, verified Claude Code skill and prompt template repos. Mix of:
- Installable SKILL.md skills (e.g. obra/superpowers, anthropics examples)
- Useful CLAUDE.md patterns and prompt templates
- Diverse authors (not all from one person)
- Practical focus for the target audience (vibe coders, solopreneurs, indie hackers)

With rotation from step 1, 25 skills gives nearly a month of daily variety before any repeats.

## Technical Considerations

**No new dependencies or APIs** — This is a ~15-line function addition and a config edit. No GitHub API, no cache files, no new environment variables.

**Frontend fallback** — `index.html:1661` has a hardcoded obra/superpowers fallback. Leave as-is (only fires when `quick_wins` is completely empty). Note as tech debt.

**Newsletter gap** — `newsletter.py` does not render quick_wins at all. Out of scope but worth a follow-up.

## Acceptance Criteria

- [x] `select_rotated_skill()` function in `scripts/fetcher.py` picks from pool, excludes recently-shown
- [x] Falls back to least-recently-shown when all skills exhausted
- [x] Date-seeded RNG: same skill on same day across re-runs
- [x] Remove skill dedup exemption at line 986
- [x] Skill URL recorded in `seen_urls.json` after each run (already works via line 1067-1068)
- [x] `config.json` `github_skills` cleaned: fake gist URLs removed, 20-30 real repos added
- [x] Mix of authors and skill types in the curated list

## Dependencies & Risks

- **Config commit required** — Updated `github_skills` list must be committed alongside code changes (see `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md`)
- **Small pool exhaustion** — With 25 skills and 30-day seen_urls window, repeats start after ~25 days. The fallback-to-oldest logic handles this gracefully.

## Future Consideration

If the curated list becomes a maintenance burden (pool exceeds 30+ and needs frequent updates), consider a simple GitHub API search integration. One query, no cache, merged with the static list. But that is a separate plan for later — the curated approach handles the current scale well.

## Key Files

- `scripts/fetcher.py:571-595` — `get_github_skills()` (loads from config, no changes needed)
- `scripts/fetcher.py:843-877` — `create_quick_wins()` (use rotation instead of `skills[0]`)
- `scripts/fetcher.py:982-986` — dedup exemption (remove)
- `scripts/fetcher.py:1063-1068` — seen_urls recording (already works)
- `scripts/fetcher.py:275-277` — date-seeded RNG pattern (reuse)
- `config.json:37-52` — `github_skills` (clean up, add real repos)
- `index.html:1661` — hardcoded fallback (tech debt, leave for now)

## References

- Brainstorm: `docs/brainstorms/2026-03-05-skill-rotation-and-discovery-brainstorm.md`
- YouTube rotation pattern: `scripts/fetcher.py:275-277`
- Config commit gotcha: `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md`
