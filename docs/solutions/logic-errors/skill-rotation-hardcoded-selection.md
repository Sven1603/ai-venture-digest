---
title: "Hardcoded skills[0] selection causes zero skill rotation in daily quick wins"
category: logic-errors
module: scripts/fetcher.py, config.json, index.html
tags: [skill-rotation, quick-wins, deterministic-selection, seen-urls, content-diversity, config-curation]
symptoms:
  - "Readers see the same Claude Skill every day — always the first entry in config github_skills"
  - "11 of 14 github_skills entries are fake gist URLs that 404 when clicked"
  - "Skills exempt from deduplication via content_type check, but still never rotate"
  - "Skills added to all_articles unnecessarily — they only appear in quick wins"
root_cause: "create_quick_wins() used skills[0] (hardcoded first element) instead of rotating selection; dedup exemption masked the problem by keeping skills out of the seen_urls filter, but the selection logic itself never varied"
date_solved: 2026-03-05
severity: medium
merged_pr: 12
related:
  - docs/solutions/logic-errors/source-concentration-and-display-quality.md
  - docs/solutions/security-issues/xss-and-code-review-hardening.md
---

# Hardcoded skills[0] Selection Causes Zero Skill Rotation

## Problem

Four related issues in the daily "Claude Skill" quick win:

1. **Hardcoded `skills[0]`**: `create_quick_wins()` always picked the first skill from the config list (obra/superpowers), so readers saw the same skill every single day.
2. **Fake gist URLs**: Of the 14 entries in `config.json` `github_skills`, 11 were placeholder gist URLs pointing to non-existent repos.
3. **Dedup exemption workaround**: A `content_type == 'skill'` exemption in the dedup logic kept the hardcoded skill from being filtered out after day one — masking the lack of rotation.
4. **Unescaped `win.icon`**: In `index.html`, the quick win icon field was interpolated into innerHTML without `escHtml()`, inconsistent with the XSS hardening pattern.

## Root Cause

The original implementation treated skills as a static single-item feature. `skills[0]` was "good enough" for launch, and the dedup exemption was bolted on to prevent that one skill from disappearing after day one. The fake gist URLs were never rotated into view because no rotation logic existed. The result: a permanently stale quick win slot.

## Solution

### `select_rotated_skill()` function

Added at `scripts/fetcher.py:843`:

```python
def select_rotated_skill(skills, seen, today):
    """Pick a skill the reader hasn't seen recently, date-seeded for determinism."""
    if not skills:
        return None
    available = [s for s in skills if s['url'] not in seen]
    if not available:
        # All shown — pick from the oldest-shown to maximize variety
        available = sorted(skills, key=lambda s: seen.get(s['url'], ''))[:max(1, len(skills) // 4)]
    return random.Random(today).choice(available)
```

How it works:
1. Filters the skill pool to entries whose URL is NOT in `seen_urls` (not shown within the 30-day history window).
2. If all skills have been shown (pool exhausted after ~25 days), falls back to the **oldest quarter** — sorts by last-seen date ascending, takes the bottom 25%, giving maximum time gap before a repeat.
3. Uses `random.Random(today)` with today's date string as seed for deterministic daily picks. Same pattern as YouTube search query rotation at line 275.

### Dedup exemption removal

The dedup at line 994 is now a clean filter with no special cases:

```python
all_articles = [a for a in all_articles if a['url'] not in seen]
```

Safe because skills no longer flow through `all_articles` at all — they're selected independently by `select_rotated_skill` before dedup runs.

### Skills removed from `all_articles`

Skills are loaded but not appended to the main article list:

```python
# 4. GitHub skills (curated — used for quick wins only, not main article list)
skills = get_github_skills(config)
```

They are only passed to `create_quick_wins()`, which is their sole consumer.

### Config cleanup

Replaced 11 fake gist URLs with 25 real, verified GitHub repos from diverse authors. Human-friendly display names instead of `owner/repo` slugs. Mix of official Anthropic repos, community skill collections, CLAUDE.md templates, and prompt engineering guides.

### `escHtml(win.icon)` fix

At `index.html:1825`, the icon field now uses `escHtml()` consistent with all other interpolated fields.

## Key Patterns

- **Date-seeded `random.Random(today)`**: Deterministic within a day, different across days. No global state pollution (instance-based RNG, not `random.seed()`).
- **`seen_urls` as rotation state**: No new state mechanism. The existing 30-day URL history drives both article dedup and skill rotation.
- **Oldest-quarter fallback**: `[:max(1, len(skills) // 4)]` — preserves some randomness while maximizing gap since last appearance. `max(1, ...)` prevents crashes on tiny pools.

## Gotchas

- **Pool exhaustion timing**: 25 skills / 30-day window = repeats start after ~25 days. The oldest entries age past 30 days and re-enter the fresh pool naturally.
- **Config `name` flows to reader-facing title**: The `name` field in `github_skills` becomes the `title` shown in quick wins cards via `get_github_skills()`. Typos are reader-visible.
- **Brand-new skills get priority**: Skills with no `seen_urls` entry sort first in the fallback (empty string `''` < any date string), so new additions to config appear immediately.
- **Skill URLs share the `seen_urls` namespace**: Collision with an article URL is theoretically possible but extremely unlikely given GitHub repo URL uniqueness.

## Prevention Strategies

1. **Never hardcode index selection for rotating content.** Any content pool meant to provide daily variety must use an explicit rotation mechanism. Grep for `\[0\]` on config-sourced lists that feed reader-facing content.
2. **Always validate URLs in config before committing.** Every URL should be manually verified. Consider a CI step that HEAD-requests config URLs and flags 404s.
3. **Never use dedup exemptions as workarounds.** The dedup system should apply uniformly. If a content type needs to bypass dedup, the fix is rotation logic that selects *before* dedup, not an exemption *within* dedup.
4. **Escape all config-sourced data in frontend templates.** Every field interpolated via `innerHTML` must go through `escHtml()` or `safeUrl()`. No exceptions.

## Testing Patterns

| Scenario | Assertion |
|----------|-----------|
| Determinism | Same inputs + same date = same skill across re-runs |
| Skip-seen | Skill in `seen` is not selected when others are available |
| Fallback | All seen: returned skill comes from oldest-dated quarter |
| Empty list | Returns `None`, quick wins skips the skill card |
| Single skill | Always returned even when in `seen` (`max(1, 1//4)` = 1) |

## Future Considerations

- **GitHub API discovery**: When pool exceeds 30+ and manual curation becomes burdensome, add a single GitHub search query merged with the static list. Deferred — see `docs/brainstorms/2026-03-05-skill-rotation-and-discovery-brainstorm.md`.
- **Newsletter rendering**: `newsletter.py` does not render `quick_wins` at all. Email subscribers never see the skill recommendation.
- **Frontend fallback**: `index.html:1661` has a hardcoded obra/superpowers fallback (defense in depth, not changed).

## Key Files

- `scripts/fetcher.py:843` — `select_rotated_skill()`
- `scripts/fetcher.py:854` — `create_quick_wins()` (uses rotation)
- `scripts/fetcher.py:994` — dedup (exemption removed)
- `config.json:37-63` — 25 curated skill repos
- `index.html:1825` — `escHtml(win.icon)`
- `docs/plans/2026-03-05-feat-skill-rotation-github-discovery-plan.md` — implementation plan
