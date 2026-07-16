# News-focus pivot — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reframe AI Venture Digest from teaching how to use AI into a daily AI-news digest: invert the content gatekeeper, classify items into four news categories, reweight scoring toward source-trust + recency, and restructure the web + email output around those categories.

**Architecture:** Pure aggregation (no LLM). `fetcher.py` fetches, gatekeeps (`is_newsworthy`), classifies (`classify_category`), scores (`calculate_score`), and writes `data/articles.json`. `newsletter.py` and `index.html` consume the `category` field. The four category values `releases` / `launches` / `business` / `research` are a shared contract across all three files.

**Tech stack:** Python 3.12 stdlib only (no external deps). Tests use the stdlib `unittest` module (the project has no test framework and prizes zero deps — do NOT introduce pytest). Frontend is a single `index.html` with vanilla JS/CSS.

**Spec:** `docs/brainstorms/2026-07-16-news-focus-pivot-design.md`

**Before starting:** This is code work on `main`. Create a branch first: `git checkout -b feat/news-focus-pivot`.

**On line numbers:** Line references are from the pre-edit files and **drift as tasks add/remove code** (e.g. Tasks 2-3 add functions near the top, shifting everything below). Always anchor on the **quoted code** in each step, not the line number — the quoted snippet is the source of truth for what to find and replace.

---

## File structure

- `config.json` — retune filters, drop dead/obsolete keys, drop `github_skills`, rewrite YouTube queries, update tagline. (Modify)
- `scripts/fetcher.py` — new `is_newsworthy`, new `classify_category`, reworked `calculate_score`; remove `is_actionable_content`, `is_tool_content`, `select_rotated_skill`, `create_quick_wins`, `get_github_skills`; rewire call sites and `main()`. (Modify)
- `tests/test_fetcher_news.py` — new stdlib `unittest` tests for the three pure functions. (Create)
- `scripts/newsletter.py` — update `category_info` map to the four categories. (Modify)
- `index.html` — remove Quick Wins + standalone Launches sections, split Must Reads into four category sections, keep Videos/More-Podcasts/Twitter/Featured-Podcast, update TOC + scroll-spy + archive filter + tagline. (Modify)

**Category contract (memorize):** fetcher emits `category` ∈ {`releases`, `launches`, `business`, `research`} for grid articles. YouTube items keep `category: 'video'` (they route to the Videos section via `video_url`), podcasts keep `podcast`, tweets keep `twitter`. newsletter `category_info` and index.html sections key off the same four values.

---

## Task 1: Config — retune filters and sources

**Files:**
- Modify: `config.json`

- [ ] **Step 1: Retune the `filters` block**

In `config.json`, replace the `filters` object (currently lines ~88-102) with:

```json
  "filters": {
    "max_age_hours": 48,
    "max_articles": 30,
    "reputation_weight": 0.30,
    "relevance_weight": 0.20,
    "recency_weight": 0.30,
    "max_per_source": 2,
    "source_caps": {
      "Product Hunt": 5
    },
    "youtube_min_views": 500,
    "youtube_min_subscribers": 1000
  },
```

Changes: `max_age_hours` 72→48; reputation 0.25→0.30; relevance 0.30→0.20; recency 0.20→0.30; **removed** `engagement_weight` and `strict_actionable` — both are dead config, present in `config.json` but never read by any script (verified via grep).

- [ ] **Step 2: Drop the `github_skills` source**

Delete the entire `"github_skills": [ ... ]` array from `config.json.sources` (currently lines ~37-63).

- [ ] **Step 3: Rewrite `youtube_search_queries` toward news**

Replace the `youtube_search_queries` array with news-oriented queries:

```json
  "youtube_search_queries": [
    "AI news this week",
    "new AI model announcement",
    "OpenAI announcement",
    "Anthropic Claude announcement",
    "Google Gemini announcement",
    "AI product launch",
    "AI industry news",
    "new AI tool launch",
    "AI funding acquisition news",
    "AI research breakthrough explained"
  ],
```

- [ ] **Step 4: Update the tagline/description**

In `config.json`, change:

```json
  "description": "The AI news that matters — for people who build",
```

- [ ] **Step 5: Validate JSON and commit**

Run: `python3 -c "import json; json.load(open('config.json')); print('OK')"`
Expected: `OK`

```bash
git add config.json
git commit -m "config: retune filters and sources for news focus"
```

---

## Task 2: `is_newsworthy()` — the inverted gatekeeper

**Files:**
- Create: `tests/test_fetcher_news.py`
- Modify: `scripts/fetcher.py` (add function near the current `is_actionable_content`, fetcher.py:34)

- [ ] **Step 1: Write the failing test**

Create `tests/test_fetcher_news.py`:

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import fetcher  # noqa: E402


class TestIsNewsworthy(unittest.TestCase):
    def test_accepts_model_release(self):
        self.assertTrue(fetcher.is_newsworthy(
            "Anthropic introducing Claude Opus 4.8", "New flagship model now available"))

    def test_accepts_funding_news(self):
        self.assertTrue(fetcher.is_newsworthy(
            "AI startup raises $50M Series B", "Funding round led by a16z"))

    def test_rejects_non_ai(self):
        self.assertFalse(fetcher.is_newsworthy(
            "Best hiking trails in the Alps", "A guide to mountain routes"))

    def test_rejects_wildlife_noise(self):
        self.assertFalse(fetcher.is_newsworthy(
            "Giant anaconda filmed in the Amazon rainforest", "wildlife documentary"))

    def test_rejects_raw_paper(self):
        self.assertFalse(fetcher.is_newsworthy(
            "New arxiv paper on variational autoencoders", "research paper analysis"))

    def test_rejects_drama(self):
        self.assertFalse(fetcher.is_newsworthy(
            "Sam vs Elon: the AI beef continues", "lawsuit drama"))

    def test_rejects_roundup(self):
        self.assertFalse(fetcher.is_newsworthy(
            "This week in AI: weekly roundup", "your weekly digest"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_fetcher_news.TestIsNewsworthy -v`
Expected: FAIL with `AttributeError: module 'fetcher' has no attribute 'is_newsworthy'`

- [ ] **Step 3: Implement `is_newsworthy`**

Add to `scripts/fetcher.py` (import `re` at top if not already present — it is, `VIDEO_ID_RE` uses it):

```python
def is_newsworthy(title, description=''):
    """
    Is this AI news worth surfacing for a non-engineer builder audience?
    Inverts the old is_actionable_content gate: news/announcements are welcome,
    how-to content is no longer required.
    """
    text = (title + ' ' + description).lower()

    hard_exclude = [
        # Nature/wildlife noise (wrong-channel content)
        'anaconda', 'jungle', 'amazon rainforest', 'wildlife',
        'nature documentary', 'expedition', 'predator', 'prey',
        # Raw academic papers
        'arxiv', 'research paper', 'paper review', 'paper analysis',
        'variational autoencoder', 'proof that', 'theorem',
        # Drama / controversy
        'drama', 'controversy', 'beef', 'feud', 'lawsuit', 'sues', 'slams',
        'clap back', 'shots fired',
        # Roundups / other digests
        'weekly roundup', 'news recap', 'this week in', 'weekly digest',
        'daily digest', 'top 10', 'top ten',
    ]
    if any(kw in text for kw in hard_exclude):
        return False

    # Substring-safe AI tokens
    strong_ai = [
        'llm', 'gpt', 'claude', 'gemini', 'chatgpt', 'openai', 'anthropic',
        'copilot', 'generative ai', 'machine learning', 'neural network',
        'mistral', 'llama', 'deepseek', 'grok', 'perplexity', 'hugging face',
    ]
    if any(kw in text for kw in strong_ai):
        return True

    # Word-boundary tokens (avoid matching 'said', 'chain', etc.)
    return bool(re.search(r'\b(ai|a\.i\.|agent|agents|model|models)\b', text))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_fetcher_news.TestIsNewsworthy -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_fetcher_news.py scripts/fetcher.py
git commit -m "feat: add is_newsworthy news gatekeeper"
```

---

## Task 3: `classify_category()` — assign one of four categories

**Files:**
- Modify: `scripts/fetcher.py` (add function after `is_newsworthy`)
- Modify: `tests/test_fetcher_news.py` (add test class)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fetcher_news.py`:

```python
class TestClassifyCategory(unittest.TestCase):
    def test_release(self):
        self.assertEqual(fetcher.classify_category(
            "Introducing Claude Opus 4.8", "now available in the API"), 'releases')

    def test_business(self):
        self.assertEqual(fetcher.classify_category(
            "OpenAI acquires io for $6.5B", "acquisition deal"), 'business')

    def test_research(self):
        self.assertEqual(fetcher.classify_category(
            "New study shows LLMs beat humans on benchmark", "research"), 'research')

    def test_launch_from_source_type(self):
        self.assertEqual(fetcher.classify_category(
            "CoolAI App", "a neat new app", source_type='product_launch'), 'launches')

    def test_defaults_to_business(self):
        self.assertEqual(fetcher.classify_category(
            "AI adoption grows across enterprises", "industry trends"), 'business')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_fetcher_news.TestClassifyCategory -v`
Expected: FAIL with `AttributeError: module 'fetcher' has no attribute 'classify_category'`

- [ ] **Step 3: Implement `classify_category`**

Add to `scripts/fetcher.py`:

```python
def classify_category(title, description='', source_type=''):
    """
    Classify a newsworthy item into exactly one of the four news categories:
    releases / launches / business / research. Order matters (most specific first);
    'business' is the catch-all for general industry/strategy news.
    """
    text = (title + ' ' + description).lower()

    research = ['study', 'benchmark', 'research shows', 'breakthrough',
                'paper finds', 'evaluation', 'outperforms', 'beats humans']
    if any(k in text for k in research):
        return 'research'

    if source_type == 'product_launch' or any(k in text for k in
            ['new app', 'new tool', 'we built', 'built with', 'just launched',
             'launching', 'now on product hunt']):
        return 'launches'

    releases = ['introducing', 'now available', 'generally available',
                'new model', 'new feature', 'rolls out', 'release', 'released',
                'unveils', 'announces', 'update to', 'version']
    if any(k in text for k in releases):
        return 'releases'

    business = ['raises', 'raised', 'funding', 'valuation', 'acquires',
                'acquisition', 'partnership', 'partners with', 'ipo',
                'regulation', 'policy', 'deal']
    if any(k in text for k in business):
        return 'business'

    return 'business'
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_fetcher_news.TestClassifyCategory -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/fetcher.py tests/test_fetcher_news.py
git commit -m "feat: add classify_category for four news categories"
```

---

## Task 4: Rework `calculate_score` for news

**Files:**
- Modify: `scripts/fetcher.py:787-836` (`calculate_score`)
- Modify: `tests/test_fetcher_news.py`

- [ ] **Step 1: Write the failing test**

Append a test class to `tests/test_fetcher_news.py` (before the `if __name__` block — move that block to the end):

```python
class TestCalculateScore(unittest.TestCase):
    CONFIG = {
        'topics': ['ai', 'agents', 'model'],
        'filters': {'reputation_weight': 0.30, 'relevance_weight': 0.20,
                    'recency_weight': 0.30, 'max_age_hours': 48},
    }

    def test_significance_bonus_applied(self):
        base = fetcher.calculate_score(
            {'title': 'AI thing', 'description': 'ai model', 'reputation': 0.5},
            self.CONFIG)
        boosted = fetcher.calculate_score(
            {'title': 'Introducing new model', 'description': 'now available ai',
             'reputation': 0.5}, self.CONFIG)
        self.assertGreater(boosted, base)

    def test_reputation_contributes(self):
        low = fetcher.calculate_score(
            {'title': 'ai model', 'reputation': 0.1}, self.CONFIG)
        high = fetcher.calculate_score(
            {'title': 'ai model', 'reputation': 1.0}, self.CONFIG)
        self.assertGreater(high, low)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_fetcher_news.TestCalculateScore -v`
Expected: FAIL — `test_significance_bonus_applied` fails because the current function gives no significance bonus (both equal).

- [ ] **Step 3: Replace the content-type + strong-keyword block**

In `scripts/fetcher.py`, replace lines 802-818 (the `type_bonuses` dict through the `strong_actionable` bonus) with:

```python
    # Significance bonus — news importance signals
    significance_keywords = [
        'introducing', 'now available', 'generally available', 'launches',
        'launched', 'acquires', 'acquisition', 'raises', 'partnership',
        'new model', 'release', 'unveils',
    ]
    if any(kw in text for kw in significance_keywords):
        score += 0.15
```

Leave the reputation, relevance, and recency blocks unchanged (they already read the retuned weights from config).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_fetcher_news.TestCalculateScore -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full test module**

Run: `python3 -m unittest tests.test_fetcher_news -v`
Expected: PASS (14 tests total)

- [ ] **Step 6: Commit**

```bash
git add scripts/fetcher.py tests/test_fetcher_news.py
git commit -m "feat: reweight calculate_score with news significance bonus"
```

---

## Task 5: Rewire fetcher call sites and remove teaching machinery

**Files:**
- Modify: `scripts/fetcher.py` — YouTube (300-352), engineering blogs (525-568), Product Hunt (704-720), `main()` (955-1093); delete `is_actionable_content` (34-96), `is_tool_content` (99-120), `get_github_skills` (571-595), `select_rotated_skill` (843-851), `create_quick_wins` (854-914).

- [ ] **Step 1: Retarget the YouTube classifier**

Replace fetcher.py:323-331 (the `is_actionable_content` / `is_tool_content` branch) with:

```python
            if not is_newsworthy(title, desc):
                continue
            content_type = 'video'
            category = 'video'
```

(YouTube items route to the Videos section via `video_url`; their category stays `video`, outside the four-section grid.)

- [ ] **Step 2: Retarget the engineering-blog classifier**

Replace fetcher.py:548-559 (the `is_actionable_content` / `is_tool_content` branches) with:

```python
                if is_newsworthy(title, desc):
                    article['category'] = classify_category(title, desc)
                    article['content_type'] = article['category']
                    articles.append(article)
                    accepted += 1
                    print(f"  ✓ {name}: {title[:50]}...")
```

Update the "No actionable content" message (fetcher.py:562) to `f"  - {name}: No newsworthy content"` and the summary print (567) to `f"  → Found {len(articles)} newsworthy blog posts"`.

- [ ] **Step 3: Retarget the Product Hunt classifier**

Replace fetcher.py:716-717 with:

```python
                    item['category'] = 'launches'
                    item['content_type'] = 'launches'
```

- [ ] **Step 4: Delete obsolete functions**

Delete these functions entirely from `scripts/fetcher.py`:
- `is_actionable_content` (34-96)
- `is_tool_content` (99-120)
- `get_github_skills` (571-595)
- `select_rotated_skill` (843-851)
- `create_quick_wins` (854-914)

Keep `is_podcast_relevant` and `get_featured_podcast` (still used).

- [ ] **Step 5: Update `main()` — remove skills + quick wins**

In `main()`:
- Delete the "GitHub skills" block (fetcher.py:976-977: `skills = get_github_skills(config)`).
- Delete the "Create Quick Wins" block (fetcher.py:1021-1025: `today = ...`, `quick_wins = create_quick_wins(...)`, and the print).
- In the `output` dict (1051-1060), remove the `'quick_wins': quick_wins,` line. Keep `featured_podcast`, `twitter_posts`, `categories`, `articles`.
- In the "Record shown URLs" block (1074-1084), delete the `for qw in output.get('quick_wins', [])` loop. Keep the `articles`, `featured_podcast`, and `twitter_posts` recording loops (seen_urls dedup stays).
- Remove the final `print(f"   - {len(quick_wins)} quick wins")` line (1092).

- [ ] **Step 6: Verify the module imports and the fetcher is syntactically whole**

Run: `python3 -c "import sys; sys.path.insert(0,'scripts'); import fetcher; print('import OK'); assert not hasattr(fetcher,'is_actionable_content'); assert not hasattr(fetcher,'create_quick_wins'); print('cleanup OK')"`
Expected: `import OK` then `cleanup OK`

- [ ] **Step 7: Run tests again (guard against breakage)**

Run: `python3 -m unittest tests.test_fetcher_news -v`
Expected: PASS (14 tests)

- [ ] **Step 8: Commit**

```bash
git add scripts/fetcher.py
git commit -m "refactor: rewire fetcher to news gatekeeper, remove teaching machinery"
```

---

## Task 6: Newsletter — categories, stats, and copy

The newsletter already groups by `category` (there is no quick-wins block). But it still carries teaching leftovers: a hardcoded "TUTORIALS" stat that is now always zero, "for venture builders" footer copy in both the HTML and plain-text versions, and a plain-text generator that renders a flat list rather than the four category sections the design calls for. This task fixes all of it. (The subject line at newsletter.py:361 already leads with the top story's title — leave it.)

**Files:**
- Modify: `scripts/newsletter.py` — `category_info` (55-62), section loop (66), stats bar (159-163), HTML footer (199), `generate_newsletter_text` (220-250).

- [ ] **Step 1: Update `category_info`**

Replace the `category_info` dict (newsletter.py:55-62) with:

```python
    category_info = {
        'releases': {'emoji': '🚀', 'title': 'Releases'},
        'launches': {'emoji': '🆕', 'title': 'Launches'},
        'business': {'emoji': '📈', 'title': 'Business & Strategy'},
        'research': {'emoji': '🔬', 'title': 'Research'},
    }
```

- [ ] **Step 2: Order the HTML sections deterministically**

The email iterates `by_category.items()` in insertion order (newsletter.py:66). Replace that loop header so sections render in fixed order regardless of article order:

```python
    order = ['releases', 'launches', 'business', 'research']
    for category in order:
        items = by_category.get(category)
        if not items:
            continue
        info = category_info.get(category, {'emoji': '📌', 'title': category.title()})
```

(Remove the old `for category, items in by_category.items():` line and its inline `info = ...` lookup.)

- [ ] **Step 3: Replace the dead "TUTORIALS" stat with a "SOURCES" stat**

Replace the third stat cell (newsletter.py:159-163) — which counts `content_type == 'tutorial'` and is now always 0 — with a distinct-source count:

```python
                  <td align="center" width="33%">
                    <span style="color: #8b5cf6; font-size: 24px; font-weight: 700;">{len(set(a.get('source', '') for a in top_articles))}</span>
                    <br>
                    <span style="color: #a0a0b0; font-size: 12px;">SOURCES</span>
                  </td>
```

- [ ] **Step 4: Update the HTML footer copy**

Replace the footer line (newsletter.py:199) `Curated with AI for venture builders` with:

```html
                      The AI news that matters — for people who build
```

- [ ] **Step 5: Group the plain-text version by category and retag its footer**

Replace the article loop + footer in `generate_newsletter_text` (newsletter.py:235-248) so the plain-text email groups by the same four categories in the same order:

```python
    by_category = {}
    for article in top_articles:
        by_category.setdefault(article.get('category', 'business'), []).append(article)

    order = ['releases', 'launches', 'business', 'research']
    titles = {'releases': 'RELEASES', 'launches': 'LAUNCHES',
              'business': 'BUSINESS & STRATEGY', 'research': 'RESEARCH'}
    for category in order:
        items = by_category.get(category)
        if not items:
            continue
        lines.append(titles[category])
        lines.append("-" * len(titles[category]))
        for article in items:
            lines.extend([
                f"• {article['title']}",
                f"  Source: {article['source']}",
                f"  {article.get('description', '')[:150]}...",
                f"  → {article['url']}",
                "",
            ])

    lines.extend([
        "-" * 50,
        "The AI news that matters — for people who build",
        "Unsubscribe: *|UNSUB|*",
    ])
```

(This replaces the old `for i, article in enumerate(top_articles, 1):` loop and the old `lines.extend([...])` footer.)

- [ ] **Step 6: Verify generation offline (no send)**

This requires a `data/articles.json`. If Task 8 has not run yet, craft a minimal fixture:

Run:
```bash
python3 -c "import json,os; os.makedirs('data',exist_ok=True); json.dump({'articles':[{'title':'Introducing X','url':'https://e.com','description':'now available','source':'S','category':'releases','content_type':'releases'}]}, open('data/articles.json','w'))"
python3 scripts/newsletter.py
```
Expected: prints "Missing Mailchimp credentials", saves a template to `templates/`, no traceback. Open the saved HTML and confirm it contains `Releases`, `SOURCES` (not `TUTORIALS`), and the new footer tagline.

- [ ] **Step 7: Commit**

```bash
git add scripts/newsletter.py
git commit -m "feat: reframe newsletter around news categories and copy"
```

---

## Task 7: Frontend — restructure index.html into category sections

**REQUIRED FIRST:** Per `CLAUDE.md`, invoke the `frontend-design` skill before any frontend edits, and use the screenshot workflow (`node screenshot.mjs http://localhost:8000`) to verify. Serve locally on :8000; never screenshot a `file://` URL.

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Remove the Quick Wins section**

Delete the `#quickWinsSection` markup (index.html:1355-1363), the `renderQuickWins()` function (around index.html:1816) and its call in `renderAll()` (index.html:1806-1816 area), and the CSS for `.quick-wins-grid` / `.quick-win-*` (index.html:333-430). Also remove the `quick_wins` archive merge line (index.html:2105).

- [ ] **Step 2: Replace Must Reads with four category sections**

Replace the single `#mustReadsSection` (index.html:1396-1407) with four sections in this fixed order, each with its own grid container:

```html
        <section id="releasesSection" class="section-white">
            <div class="container">
                <div class="section-header"><h2 class="section-title">🚀 Releases</h2></div>
                <div class="must-reads-list" id="releasesList"></div>
            </div>
        </section>
        <section id="launchesCatSection" class="section-cream">
            <div class="container">
                <div class="section-header"><h2 class="section-title">🆕 Launches</h2></div>
                <div class="must-reads-list" id="launchesCatList"></div>
            </div>
        </section>
        <section id="businessSection" class="section-white">
            <div class="container">
                <div class="section-header"><h2 class="section-title">📈 Business &amp; Strategy</h2></div>
                <div class="must-reads-list" id="businessList"></div>
            </div>
        </section>
        <section id="researchSection" class="section-cream">
            <div class="container">
                <div class="section-header"><h2 class="section-title">🔬 Research</h2></div>
                <div class="must-reads-list" id="researchList"></div>
            </div>
        </section>
```

- [ ] **Step 3: Add a category-section renderer**

Find the existing must-reads render function (the one that populated `#mustReadsList` from `articles`). Replace it with a loop that renders each category into its list and hides empty sections. Reuse the existing `must-read-item` markup builder and the `escHtml()` / `safeUrl()` helpers. Example shape:

```javascript
        function renderCategorySections() {
            const cats = [
                ['releases', 'releasesList', 'releasesSection'],
                ['launches', 'launchesCatList', 'launchesCatSection'],
                ['business', 'businessList', 'businessSection'],
                ['research', 'researchList', 'researchSection'],
            ];
            cats.forEach(([cat, listId, sectionId]) => {
                const items = articles.filter(a => a.category === cat && !a.video_url);
                const section = document.getElementById(sectionId);
                if (!items.length) { section.style.display = 'none'; return; }
                section.style.display = '';
                document.getElementById(listId).innerHTML =
                    items.map(renderMustReadItem).join('');
            });
        }
```

If the current code builds the item HTML inline rather than via a helper, extract that HTML builder into `renderMustReadItem(a)` first (keeping the exact same markup + `escHtml`/`safeUrl` usage), then call it from the loop. Call `renderCategorySections()` from `renderAll()` where `renderMustReads()`/`renderQuickWins()` used to be called.

- [ ] **Step 4: Remove the standalone Product Hunt Launches section**

Delete `#launchesSection` markup (index.html:1467-1475) and its renderer + CSS (`.launches-grid`). Product Hunt items now carry `category: 'launches'` and render in the Launches category section from Step 2.

- [ ] **Step 5: Keep Videos, More Podcasts, Twitter, Featured Podcast**

Leave `#videoSection`, `#morePodcastsSection`, `#twitterSection`, and `#featuredPodcast` markup and renderers unchanged. Confirm they still render after the four category sections.

- [ ] **Step 6: Update TOC and scroll-spy**

Update the section list in `buildTOC()` (index.html:1694-1720) and the scroll-spy observer list to: Releases, Launches, Business & Strategy, Research, Videos, More Podcasts, Twitter (drop Quick Wins and the old standalone Launches; drop Quick Hits only if it was removed — otherwise keep). Use the new section ids from Step 2.

- [ ] **Step 7: Update archive filter options**

In the archive modal `<select id="archiveFilter">` (index.html:1531-1536), replace the old category options with: All, Releases, Launches, Business, Research, Videos. Update any `openArchive('...')` calls and the archive filtering logic that referenced `quick_wins` / old categories.

- [ ] **Step 8: Update the hero tagline copy**

Update the hero subtitle text to the new tagline: "The AI news that matters — for people who build." (Search the hero markup near index.html:1335 for the old "Actionable AI content…" string.)

- [ ] **Step 9: Serve, screenshot, and verify**

```bash
python3 -m http.server 8000 &   # if not already running
node screenshot.mjs http://localhost:8000 news-pivot
```
Read the screenshot from `temporary screenshots/`. Verify: no Quick Wins section; four category sections render in order with items; empty categories are hidden; Videos/Podcasts/Twitter still present; tagline updated; no console errors. Do at least two screenshot passes, fixing mismatches between them.

- [ ] **Step 10: Commit**

```bash
git add index.html
git commit -m "feat: restructure frontend into four news category sections"
```

---

## Task 8: End-to-end pipeline verification

**Files:** none (verification only)

- [ ] **Step 1: Run the fetcher against live sources**

Run: `python3 scripts/fetcher.py`
Expected: completes without traceback; prints a content summary. (YouTube needs `YOUTUBE_API_KEY`; if absent it degrades gracefully — that is acceptable for this check.)

- [ ] **Step 2: Verify the category distribution and schema**

Run:
```bash
python3 -c "
import json; d=json.load(open('data/articles.json'))
assert 'quick_wins' not in d, 'quick_wins should be gone'
cats={}
for a in d['articles']: cats[a.get('category')]=cats.get(a.get('category'),0)+1
print('categories:', cats)
grid={'releases','launches','business','research'}
assert grid & set(cats), 'expected at least one news category'
print('OK')
"
```
Expected: prints a category distribution containing news categories and `OK`. (`video`/`podcast`/`twitter` may also appear — those render in their own sections.)

- [ ] **Step 3: Generate the newsletter offline**

Run: `python3 scripts/newsletter.py` (no Mailchimp creds set)
Expected: "Missing Mailchimp credentials", template saved to `templates/`, no traceback. Confirm the HTML groups items under the four category headers.

- [ ] **Step 4: Serve the site and confirm it reads the fresh data**

Run: `python3 -m http.server 8000` and screenshot with `node screenshot.mjs http://localhost:8000 e2e`. Confirm the four category sections populate from the freshly fetched `data/articles.json`.

- [ ] **Step 5: Final commit (data snapshot is regenerated by CI, so do not force local data)**

Note: `data/articles.json` is regenerated by CI and often conflicts with local runs — do not fret over committing it. Commit only if the working tree has intended source changes left:

```bash
git status
# commit any remaining intended changes only
```

---

## Self-review notes (author checklist, already applied)

- **Spec coverage:** gatekeeper (Task 2), categories (Task 3), scoring reweight + dead `engagement_weight` removal (Tasks 1, 4), source changes incl. `github_skills` drop + YouTube requery (Tasks 1, 5), quick-wins/skills removal (Task 5), `seen_urls` retained (Task 5 Step 5 keeps the dedup loops), newsletter category map (Task 6), frontend restructure incl. Launches merge + kept Videos/Podcasts/Twitter (Task 7), tagline (Tasks 1, 7).
- **Category vocabulary** is consistent across Tasks 3/5/6/7: `releases` / `launches` / `business` / `research`.
- **No pytest**: all unit tests use stdlib `unittest`, matching the zero-dependency ethos.
