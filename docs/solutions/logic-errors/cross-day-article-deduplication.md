---
title: "Cross-day article deduplication in daily digest"
date: 2026-02-17
category: logic-errors
module: scripts/fetcher.py
tags: [deduplication, content-freshness, fetcher, data-pipeline, rss]
severity: medium
symptoms:
  - "~32% of daily digest articles repeat from previous day"
  - "Same RSS feed items selected across consecutive runs"
  - "No cross-run memory of previously shown content"
root_cause: "Fetcher had no persistent history of shown URLs — each run started fresh"
commit: 2c498e2
merged_pr: 2
---

# Solution: Cross-Day Article Deduplication

## Problem

The newsletter was showing duplicate articles across consecutive daily digests. RSS feeds retain items for days or weeks, so the same high-scoring article would pass through the fetcher and appear in multiple digest emails without any mechanism to prevent it.

### Symptoms
- Same article appeared 2–3 days in a row
- High-reputation sources dominated, showing the same "great" articles repeatedly
- Readers received fatigue from repeated content despite fresh sources being available

### Root Causes
1. **No persistent state** — The fetcher had no memory of previously shown articles; each run started fresh with zero history
2. **No hard age cutoff** — `config.json` had `max_age_hours: 72`, but it only *penalized* recency in scoring, never *blocked* articles outright
3. **Unused config** — The `output.archive_days: 30` setting existed but was never implemented in code
4. **Intra-run dedup only** — `api/cron/fetch.py` (Vercel handler) had deduplication logic, but only for within a single fetch run, not across days
5. **Skills re-injected daily** — GitHub skills were fetched fresh each run and always passed, appearing in every digest

## Solution Implemented

### Two New Functions in `scripts/fetcher.py`

**`load_seen_urls()` (lines 678–684)**
```python
def load_seen_urls():
    """Load URL history. Returns empty dict if file missing/corrupted."""
    try:
        with open('data/seen_urls.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
```
- Loads the persistent history file `data/seen_urls.json`
- Gracefully degradates to empty dict if file is missing or corrupted (first run, or after manual delete)
- No exceptions bubble up — keeps the fetch process resilient

**`save_seen_urls(seen, archive_days)` (lines 687–694)**
```python
def save_seen_urls(seen, archive_days):
    """Save URL history, pruning entries older than archive_days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=archive_days)).strftime('%Y-%m-%d')
    pruned = {url: date for url, date in seen.items() if date >= cutoff}
    num_pruned = len(seen) - len(pruned)
    with open('data/seen_urls.json', 'w') as f:
        json.dump(pruned, f, indent=2)
    return num_pruned
```
- Prunes entries older than the configured archive window (default: 30 days from `config.json`)
- Returns count of pruned entries for logging
- Writes UTC date strings in `YYYY-MM-DD` format for readability and debugging

### Four Insertion Points in `main()` (lines 701–831)

#### 1. Load history after config (line 708)
```python
config = load_config()
seen = load_seen_urls()
all_articles = []
```
History is loaded once, before fetching begins.

#### 2. Deduplicate before sort (lines 737–746)
```python
# Deduplicate against history (skills are exempt)
before_dedup = len(all_articles)
all_articles = [
    a for a in all_articles
    if a['url'] not in seen or a.get('content_type') == 'skill'
]
blocked = before_dedup - len(all_articles)
if blocked:
    print(f"\n🔁 Dedup: blocked {blocked} previously shown articles ({len(seen)} URLs in history)")
else:
    print(f"\n🔁 Dedup: no duplicates found ({len(seen)} URLs in history)")
```
- **Hard block** (not score penalty): any URL in history is excluded
- **Skills exemption**: `content_type == 'skill'` articles pass through even if in history
  - These are manually curated, not news feeds
  - Readers want to see new skill recommendations daily
- Logging shows dedup effectiveness and history size

#### 3. Record output URLs (lines 806–819)
```python
# Record shown URLs in history (exempt skills and default twitter posts)
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
    if tweet.get('url', '').startswith('https://x.com/') and '/' in tweet['url'].split('x.com/')[1]:
        # Only record specific tweet URLs, not generic profile fallbacks
        seen[tweet['url']] = today
```
- Records *all* output URLs after final selection (articles, quick_wins, featured_podcast, specific tweets)
- Skips default/fallback Twitter posts (profile URLs like `https://x.com/@swyx` that aren't specific tweets)
- Skips skills so they can appear in future digests
- Uses today's UTC date as the seen value

#### 4. Prune and save (lines 821–824)
```python
archive_days = config.get('output', {}).get('archive_days', 30)
num_pruned = save_seen_urls(seen, archive_days)
if num_pruned:
    print(f"🔁 Dedup: pruned {num_pruned} entries older than {archive_days} days")
```
- Reads `config.json` for archive window (default 30 days)
- Removes old entries to keep the history file compact
- Logs pruning for visibility

### Data Format: `data/seen_urls.json`

```json
{
  "https://blog.langchain.dev/rag-tutorial": "2026-02-17",
  "https://www.anthropic.com/engineering/best-practices": "2026-02-16",
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "2026-02-15",
  "https://x.com/swyx/status/1756290": "2026-02-17"
}
```
- **Key**: article URL
- **Value**: date it was first shown, as `YYYY-MM-DD` string (UTC)
- Simple, human-readable, easy to debug

### UI Enhancement: Relative Timestamps

**`formatDate()` helper in `index.html` (lines 799–815)**
```javascript
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return '';
        const now = new Date();
        const diffMs = now - date;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        if (diffHours < 1) return 'just now';
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch (e) {
        return '';
    }
}
```
- Converts article `published` dates to relative timestamps ("3h ago", "2d ago", "Feb 15")
- Integrated into multiple display sections:
  - Must Reads: `${a.source}${formatDate(a.published) ? ' · ' + formatDate(a.published) : ''}`
  - More Podcasts: `${p.source}${formatDate(p.published) ? ' · ' + formatDate(p.published) : ''}`
  - Twitter posts: `${post.source}${formatDate(post.published) ? ' · ' + formatDate(post.published) : ''}`
- Helps readers see at a glance which content is fresh vs. from archives

## Design Decisions

### Why Hard Block?
A score penalty approach would still allow old articles to appear if no better content exists. A hard block ensures variety:
- If URL appeared 3 days ago, it won't appear again in digest even if it's high-scoring
- Encourages exploring lower-reputation or less-relevant articles, broadening reader exposure
- Prevents "best article of the month" from flooding the inbox

### Why Exempt Skills?
- Skills are manually curated from a fixed list in `config.json`
- They're reference material, not breaking news
- Readers benefit from seeing the same high-quality skills recommended daily
- Different from RSS feeds, which naturally expire

### Why Specific Tweet URLs?
- `https://x.com/swyx` (profile) and `https://x.com/swyx/status/1756290` (tweet) are different URLs
- Profile URLs are fallbacks used when Nitter fails; recording them would pollute history
- Only specific tweet URLs (`/status/...`) are saved to history
- Prevents duplicate tweets from appearing on subsequent fetches

### Why UTC Dates?
- Consistent across CI/local timezones
- No DST complications
- Human-readable (`2026-02-17`) and sortable
- Standard for logs and debugging

### Why 30-Day Archive?
- `config.output.archive_days` defaults to 30 per project spec
- Balances memory (JSON file stays small) with dedup window (month-long visibility)
- After 30 days, article may appear again if it resurfaces in feeds (unlikely but possible)
- Configurable — change `archive_days` in config to adjust

## Verification

### First Run
- `seen_urls.json` doesn't exist → `load_seen_urls()` returns `{}`
- All articles pass dedup filter (no history to check)
- 34 URLs recorded at end of run (articles, quick_wins, featured_podcast, tweets)
- No pruning (nothing old enough)

### Second Run
- `seen_urls.json` loads with 34 entries from day 1
- 32 articles from RSS feeds are blocked (duplicate URLs)
- 2 new articles from other sources pass through
- Skills pass through despite being in history
- Output records 28 new URLs (overlap with day 1 expected)
- Pruning: 0 entries removed (all from today–1 day ago)

### Corrupted History
- If `data/seen_urls.json` is manually deleted or corrupted:
  - `load_seen_urls()` catches exception, returns `{}`
  - Fetch continues without dedup for that run
  - Fresh `seen_urls.json` written at end
  - No crash, no manual intervention needed

## Integration Points

The solution is **non-breaking**:
- `scripts/fetcher.py` is the only backend change
- No changes to `newsletter.py` or `api/cron/fetch.py` required
- `index.html` gains `formatDate()` for display (pure UI enhancement)
- `config.json` already had `archive_days` — no schema changes
- `data/seen_urls.json` is new but gracefully handled if missing

## Observability

**Log output added to `main()` (lines 743–746, 823–824):**
```
🔁 Dedup: blocked 32 previously shown articles (34 URLs in history)
🔁 Dedup: pruned 4 entries older than 30 days
```
- Visible in GitHub Actions logs and local test runs
- Helps operators confirm dedup is working
- URL count in history shows accumulation over time

## Related Documentation

- `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md` — Always commit data files alongside code that depends on them. Same principle applies to `seen_urls.json`.
- `docs/solutions/logic-errors/source-concentration-and-display-quality.md` — Source diversity cap follows a similar filter-before-select pattern in `fetcher.py`.
- `docs/brainstorms/2026-02-17-cross-day-deduplication-brainstorm.md` — Original brainstorm with approach comparison.
- `docs/plans/2026-02-17-feat-cross-day-article-deduplication-plan.md` — Implementation plan with acceptance criteria.

## Gotchas

- `data/seen_urls.json` will cause merge conflicts on pull after CI runs — same as `data/articles.json`, accept theirs
- The Vercel cron handler (`api/cron/fetch.py`) does NOT participate in dedup — separate code path
- Deleting `seen_urls.json` locally resets dedup (useful for testing)
- Skills are exempt from dedup but their URLs ARE recorded in history — the filter checks `content_type`, not history membership
