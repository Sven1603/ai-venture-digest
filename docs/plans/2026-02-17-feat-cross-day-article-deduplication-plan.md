---
title: "feat: Cross-day article deduplication"
type: feat
date: 2026-02-17
brainstorm: docs/brainstorms/2026-02-17-cross-day-deduplication-brainstorm.md
---

# Cross-Day Article Deduplication

## Overview

~32% of daily digest articles repeat from the previous day because the fetcher has no memory of what it showed before. Add a URL history file (`data/seen_urls.json`) that hard-blocks any article already shown within the last 30 days. Show fewer articles on slow days rather than repeats.

## Proposed Solution

A `data/seen_urls.json` file stores `{url: "YYYY-MM-DD"}` mappings. On each run, `fetcher.py` loads the history, excludes known URLs from the article pool, records newly selected URLs, and prunes entries older than 30 days. The file is auto-committed by the existing CI workflow (`git add data/`).

## Key Design Decisions

These were surfaced during brainstorm and SpecFlow analysis:

1. **Dedup insertion point:** Filter `all_articles` after fetching and scoring, but **before** the source diversity cap and special selections (quick wins, featured podcast, twitter). This way dedup reduces the pool first, then existing selection logic works on the reduced set.

2. **Static content is exempt:** Articles with `content_type == "skill"` (GitHub skills from config) bypass dedup. They are curated permanent content, not news. Without this exemption, the "Claude Skill" quick win slot would be empty after day 1.

3. **Record all output URLs:** Every URL in the final output — `articles`, `quick_wins`, `featured_podcast`, `twitter_posts` — gets added to history. This prevents tweet repeats too.

4. **Default/fallback content skipped:** URLs from `get_default_twitter_posts()` (fallback when Nitter is down) are not recorded. They are generic profile URLs, not specific content.

5. **Vercel cron handler left alone:** `api/cron/fetch.py` is a separate code path. It does not participate in dedup. If it is actively sending newsletters, that is a pre-existing issue independent of this feature.

6. **UTC dates, configurable window:** Store dates as `YYYY-MM-DD` in UTC. Read the retention window from `config["output"]["archive_days"]` (already set to 30, currently unused).

7. **No config toggle for now:** Keep it simple. To test without dedup locally, delete `data/seen_urls.json`. A config toggle can be added later if needed.

## Technical Approach

### Changes to `scripts/fetcher.py`

Two new functions + four insertion points in `main()`:

#### New functions

```python
# scripts/fetcher.py — new helper functions

def load_seen_urls():
    """Load URL history. Returns empty dict if file missing/corrupted."""
    try:
        with open('data/seen_urls.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_seen_urls(seen, archive_days):
    """Save URL history, pruning entries older than archive_days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=archive_days)).strftime('%Y-%m-%d')
    pruned = {url: date for url, date in seen.items() if date >= cutoff}
    with open('data/seen_urls.json', 'w') as f:
        json.dump(pruned, f, indent=2)
    return len(seen) - len(pruned)  # number pruned
```

#### Insertion points in `main()`

```
1. After load_config()         → seen = load_seen_urls()
2. After scoring, before sort  → filter all_articles against seen (exempt skills)
3. After building output dict  → collect all URLs from output into seen
4. Before return               → save_seen_urls(seen, archive_days)
```

Detailed pseudo-code for step 2 (the dedup filter):

```python
# scripts/fetcher.py — in main(), after scoring loop (~line 711)

before_dedup = len(all_articles)
all_articles = [
    a for a in all_articles
    if a['url'] not in seen or a.get('content_type') == 'skill'
]
blocked = before_dedup - len(all_articles)
if blocked:
    print(f"Dedup: blocked {blocked} previously shown articles "
          f"({len(seen)} URLs in history)")
```

Detailed pseudo-code for step 3 (recording output URLs):

```python
# scripts/fetcher.py — in main(), after output dict is built (~line 764)

today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
for article in output.get('articles', []):
    if article.get('content_type') != 'skill':
        seen[article['url']] = today
for qw in output.get('quick_wins', []):
    if qw.get('content_type') != 'skill':
        seen[qw['url']] = today
if output.get('featured_podcast'):
    seen[output['featured_podcast']['url']] = today
for tweet in output.get('twitter_posts', []):
    if not tweet.get('is_default'):
        seen[tweet['url']] = today
```

### New file: `data/seen_urls.json`

Committed as an empty dict `{}` in the initial PR. CI auto-commits updates on each run.

### No changes needed to

- `.github/workflows/daily-fetch.yml` — already does `git add data/`
- `scripts/newsletter.py` — reads `articles.json`, unaffected
- `scripts/run_daily.py` — just orchestrates
- `index.html` — reads `articles.json`, unaffected
- `api/cron/fetch.py` — separate code path, left alone
- `config.json` — `output.archive_days: 30` already exists

## Acceptance Criteria

- [x] Running `fetcher.py` twice in a row produces zero URL overlap between the two `articles.json` outputs (except GitHub skills)
- [x] `data/seen_urls.json` is created on first run if missing, with no crash
- [x] Corrupted `seen_urls.json` (invalid JSON) triggers graceful fallback — fetcher runs without dedup and overwrites the file
- [x] URLs older than 30 days are pruned from the history file
- [x] Dedup statistics are printed: number blocked, history size, number pruned
- [x] GitHub skills (`content_type == "skill"`) appear every day regardless of history
- [x] Default/fallback twitter posts are not recorded in history
- [x] On a "slow day" (all articles are repeats), the fetcher produces a valid but smaller `articles.json` — no crash, no error
- [x] The 30-day window reads from `config["output"]["archive_days"]`

## Edge Cases

| Scenario | Expected behavior |
|---|---|
| First run ever (no history file) | No dedup, file created, all articles pass |
| Corrupted JSON in history file | Fallback to empty history, file overwritten |
| All articles are repeats | Valid output with 0 articles, log warning |
| Same URL from two sources in one run | Intra-run dedup by existing sort/cap logic; URL recorded once |
| URL with trailing slash vs without | Treated as different URLs (acceptable — feeds use consistent URLs) |
| CI and local run same day | Both modify `seen_urls.json`; accept CI version on pull |

## References

- Brainstorm: `docs/brainstorms/2026-02-17-cross-day-deduplication-brainstorm.md`
- Fetcher main flow: `scripts/fetcher.py:678` (`main()`)
- Scoring: `scripts/fetcher.py:546` (`calculate_score()`)
- Diversity cap: `scripts/fetcher.py:716`
- GitHub skills: `scripts/fetcher.py:374` (`get_github_skills()`)
- Existing intra-run dedup pattern: `api/cron/fetch.py:318`
- CI commit step: `.github/workflows/daily-fetch.yml:38`
- Config archive_days: `config.json` → `output.archive_days`
- Documented gotcha — uncommitted config crash: `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md`
