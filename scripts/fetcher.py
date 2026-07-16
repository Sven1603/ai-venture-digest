#!/usr/bin/env python3
"""
AI Venture Digest - Actionable Content Fetcher
For venture builders who ship.

Content types:
1. Quick Wins - New tools, Claude skills, quick tutorials
2. Tutorial Videos - Step-by-step guides (NOT news/announcements)
3. Podcast Episodes - Builder-focused discussions
4. Deep Dives - Engineering blogs with practical implementations
"""

import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import re
import html
import os
import random


def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)


# ============================================================
# STRICT CONTENT FILTERS
# These are the gatekeepers - be VERY selective
# ============================================================

def is_newsworthy(title, description=''):
    """
    Is this AI news worth surfacing for a non-engineer builder audience?
    Inverts the old strict how-to-only gate: news/announcements are welcome,
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
        'drama', 'controversy', 'beef', 'feud', 'lawsuit', 'slams',
        'clap back', 'shots fired',
        # Roundups / other digests
        'weekly roundup', 'news recap', 'this week in', 'weekly digest',
        'daily digest', 'top 10', 'top ten',
    ]
    if any(kw in text for kw in hard_exclude):
        return False

    # 'sues'/'sued' need a word boundary — bare substring matches 'issues', 'pursues'
    if re.search(r'\b(sues|sued)\b', text):
        return False

    # Substring-safe AI tokens
    strong_ai = [
        'llm', 'gpt', 'claude', 'gemini', 'chatgpt', 'openai', 'anthropic',
        'copilot', 'generative ai', 'machine learning', 'neural network',
        'mistral', 'llama', 'deepseek', 'grok', 'perplexity', 'hugging face',
        'a.i.',
    ]
    if any(kw in text for kw in strong_ai):
        return True

    # Word-boundary tokens (avoid matching 'said', 'chain', etc.)
    return bool(re.search(r'\b(ai|agent|agents|model|models)\b', text))


def classify_category(title, description='', content_type=''):
    """
    Classify a newsworthy item into exactly one of the four news categories:
    releases / launches / business / research. Order matters (most specific first);
    'business' is the catch-all for general industry/strategy/funding news.
    """
    text = (title + ' ' + description).lower()

    research = ['study', 'benchmark', 'research shows', 'breakthrough',
                'paper finds', 'evaluation', 'outperforms', 'beats humans']
    if any(k in text for k in research):
        return 'research'

    launches = ['new app', 'new tool', 'we built', 'built with',
                'just launched', 'launching', 'now on product hunt']
    if content_type == 'product_launch' or any(k in text for k in launches):
        return 'launches'

    releases = ['introducing', 'now available', 'generally available',
                'new model', 'new feature', 'rolls out', 'release',
                'unveils', 'announces', 'update to', 'new version']
    if any(k in text for k in releases):
        return 'releases'

    # Catch-all: funding, M&A, partnerships, regulation, and general
    # industry/strategy news all fall here.
    return 'business'


def is_podcast_relevant(title, description=''):
    """Check if podcast episode is relevant for venture builders."""
    text = (title + ' ' + description).lower()

    relevant_topics = [
        'ai', 'llm', 'gpt', 'claude', 'agent', 'automation', 'workflow',
        'startup', 'founder', 'building', 'product', 'saas', 'indie',
        'engineering', 'developer', 'coding', 'programming',
        'rag', 'embeddings', 'vector', 'prompt'
    ]

    exclude_topics = [
        'politics', 'election', 'war', 'celebrity', 'sports',
        'healthcare policy', 'regulation'
    ]

    has_relevant = any(t in text for t in relevant_topics)
    has_exclude = any(t in text for t in exclude_topics)

    return has_relevant and not has_exclude


# ============================================================
# RSS FETCHING
# ============================================================

def extract_thumbnail(entry, content=''):
    """Extract thumbnail URL from RSS entry."""
    # Check media:thumbnail
    for child in entry:
        if 'thumbnail' in child.tag.lower():
            url = child.get('url') or child.text
            if url:
                return url
        if 'content' in child.tag.lower() and child.get('url'):
            if 'image' in child.get('type', ''):
                return child.get('url')
        if 'enclosure' in child.tag.lower():
            if 'image' in child.get('type', ''):
                return child.get('url')

    # Look for img tag in content
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
    if img_match:
        return img_match.group(1)

    return None


def fetch_rss(url, source_name, reputation, content_type='article'):
    """Fetch and parse RSS feed."""
    articles = []

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 AI-Venture-Digest/2.0'
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8', errors='ignore')

        root = ET.fromstring(content)
        items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

        for item in items[:15]:
            title = item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title') or ''
            link = item.findtext('link') or ''
            description = (item.findtext('description')
                           or item.findtext('{http://www.w3.org/2005/Atom}summary')
                           or item.findtext('{http://www.w3.org/2005/Atom}content')
                           or '')
            pub_date = (item.findtext('pubDate')
                        or item.findtext('{http://www.w3.org/2005/Atom}published')
                        or item.findtext('{http://www.w3.org/2005/Atom}updated')
                        or '')

            # Atom link handling
            if not link:
                link_elem = item.find('{http://www.w3.org/2005/Atom}link')
                if link_elem is not None:
                    link = link_elem.get('href', '')

            # Clean description
            description = re.sub(r'<[^>]+>', '', description)
            description = html.unescape(description)[:300]

            thumbnail = extract_thumbnail(item, description)

            # Handle video URLs
            video_url = None
            if 'youtube.com' in link or 'youtu.be' in link:
                video_url = link
                yt_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', link)
                if yt_match and not thumbnail:
                    thumbnail = f"https://img.youtube.com/vi/{yt_match.group(1)}/hqdefault.jpg"

            # Handle podcast duration
            podcast_duration = None
            if content_type == 'podcast':
                duration_elem = item.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}duration')
                if duration_elem is not None:
                    podcast_duration = duration_elem.text

            if title and link:
                articles.append({
                    'title': html.unescape(title.strip()),
                    'url': link.strip(),
                    'description': description.strip(),
                    'source': source_name,
                    'reputation': reputation,
                    'published': pub_date,
                    'thumbnail': thumbnail,
                    'video_url': video_url,
                    'content_type': content_type,
                    'podcast_duration': podcast_duration,
                    'fetched_at': datetime.now().isoformat()
                })

    except Exception as e:
        print(f"  ⚠ Error fetching {source_name}: {e}")

    return articles


# ============================================================
# CONTENT FETCHERS
# ============================================================

VIDEO_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,20}$')


def _safe_int(val, default=0):
    """Safely cast to int, returning default on failure."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def fetch_youtube_search(config):
    """
    Fetch tutorial videos via YouTube Data API v3 search.
    Picks 3 random queries (date-seeded) from config, applies strict filters.
    Gracefully skips if YOUTUBE_API_KEY is missing or API fails.
    """
    print("\n🎬 Fetching YouTube tutorials via search API...")
    api_key = os.environ.get('YOUTUBE_API_KEY', '')
    if not api_key:
        print("  ⚠ YOUTUBE_API_KEY not set — skipping YouTube search")
        return []

    queries = config.get('youtube_search_queries', [])

    # Deterministic daily selection (reproducible CI reruns)
    rng = random.Random(datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    selected = rng.sample(queries, min(3, len(queries)))

    published_after = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    videos = []
    seen_ids = set()

    for query in selected:
        print(f"  🔍 Searching: {query}")
        params = urllib.parse.urlencode({
            'part': 'snippet',
            'type': 'video',
            'q': query,
            'maxResults': 10,
            'order': 'date',
            'publishedAfter': published_after,
            'relevanceLanguage': 'en',
            'key': api_key,
        })
        url = f"https://www.googleapis.com/youtube/v3/search?{params}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 AI-Venture-Digest/2.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print("  ⚠ YouTube API quota exhausted or key disabled (403) — stopping search")
                break
            print(f"  ⚠ YouTube API error ({e.code}): {e.reason}")
            continue
        except Exception as e:
            print(f"  ⚠ YouTube search failed for query '{query}'")
            continue

        for item in data.get('items', []):
            snippet = item.get('snippet', {})
            video_id = item.get('id', {}).get('videoId', '')
            if not video_id or not VIDEO_ID_RE.match(video_id):
                continue
            if video_id in seen_ids:
                continue
            seen_ids.add(video_id)

            title = html.unescape(snippet.get('title', ''))
            desc = html.unescape(snippet.get('description', ''))[:300]

            if not is_newsworthy(title, desc):
                continue
            content_type = 'video'
            category = 'video'

            # video_url must be truthy — routes to Videos section, not Must Reads (index.html)
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            videos.append({
                'title': title,
                'url': video_url,
                'description': desc,
                'source': snippet.get('channelTitle', 'YouTube'),
                'reputation': 0.85,
                'published': snippet.get('publishedAt', ''),
                'thumbnail': f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                'video_url': video_url,
                'content_type': content_type,
                'fetched_at': datetime.now().isoformat(),
                'category': category,
                'video_id': video_id,
                'channel_id': snippet.get('channelId', ''),
            })
            print(f"  ✓ {snippet.get('channelTitle', '?')}: {title[:50]}...")

    print(f"  → Found {len(videos)} newsworthy videos")

    # Enrich with statistics and apply quality filter
    videos = fetch_youtube_stats(videos, config)

    # Remove internal fields (not needed downstream)
    for v in videos:
        v.pop('video_id', None)
        v.pop('channel_id', None)

    return videos


def _fetch_video_statistics(api_key, video_ids):
    """Batch fetch video statistics. Returns dict {video_id: stats} or None on failure."""
    if not video_ids:
        return {}
    params = urllib.parse.urlencode({
        'part': 'statistics',
        'id': ','.join(video_ids[:50]),
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
    except Exception:
        print("  ⚠ YouTube videos.list failed unexpectedly")
        return None


def _fetch_channel_statistics(api_key, channel_ids):
    """Batch fetch channel statistics. Returns dict {channel_id: stats} or None on failure."""
    if not channel_ids:
        return {}
    params = urllib.parse.urlencode({
        'part': 'statistics',
        'id': ','.join(channel_ids[:50]),
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
            stats.setdefault('hiddenSubscriberCount', False)
            result[item['id']] = stats
        return result
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("  ⚠ YouTube API quota exhausted on channels.list (403)")
        else:
            print(f"  ⚠ YouTube channels.list error ({e.code}): {e.reason}")
        return None
    except Exception:
        print("  ⚠ YouTube channels.list failed unexpectedly")
        return None


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
    video_ids = [v['video_id'] for v in videos if v.get('video_id')]
    channel_ids = list({v['channel_id'] for v in videos if v.get('channel_id')})

    # Batch fetch statistics
    print("  📊 Fetching video & channel statistics...")
    video_stats = _fetch_video_statistics(api_key, video_ids)
    channel_stats = _fetch_channel_statistics(api_key, channel_ids)

    # If both API calls failed, return videos unfiltered
    if video_stats is None and channel_stats is None:
        print("  ⚠ Both stats calls failed — skipping quality filter")
        return videos

    # Apply hard gates
    filtered = []
    for v in videos:
        vid = v.get('video_id', '')
        cid = v.get('channel_id', '')

        # If a video is missing from stats response (deleted/private), skip it
        if video_stats is not None and vid and vid not in video_stats:
            print(f"    ✗ Skipped (not in stats): {v['title'][:60]}")
            continue

        vs = video_stats.get(vid, {}) if video_stats else {}
        cs = channel_stats.get(cid, {}) if channel_stats else {}

        views = _safe_int(vs.get('viewCount', '0'))
        subs = _safe_int(cs.get('subscriberCount', '0'))
        hidden_subs = cs.get('hiddenSubscriberCount', False)

        # Hard gate: both must fail to be dropped
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


def fetch_podcasts(config):
    """
    Fetch podcast episodes for builders.
    Filter for AI/startup/building topics.
    """
    print("\n🎙️ Fetching podcasts...")
    episodes = []

    podcasts = config['sources'].get('podcasts', [])

    for podcast in podcasts:
        name = podcast['name']
        url = podcast['url']
        reputation = podcast['reputation']

        try:
            podcast_episodes = fetch_rss(url, name, reputation, 'podcast')
            accepted = 0

            for ep in podcast_episodes[:5]:  # Max 5 per podcast
                if is_podcast_relevant(ep['title'], ep.get('description', '')):
                    ep['category'] = 'podcast'
                    ep['is_podcast'] = True
                    episodes.append(ep)
                    accepted += 1
                    print(f"  ✓ {name}: {ep['title'][:50]}...")

            if accepted == 0:
                print(f"  - {name}: No relevant episodes")

        except Exception as e:
            print(f"  ⚠ {name}: {e}")

    print(f"  → Found {len(episodes)} relevant podcast episodes")
    return episodes


def fetch_engineering_blogs(config):
    """
    Fetch from engineering blogs.
    Prioritize practical implementation content.
    """
    print("\n📝 Fetching engineering blogs...")
    articles = []

    feeds = config['sources'].get('rss_feeds', [])

    for feed in feeds:
        name = feed['name']
        url = feed['url']
        reputation = feed['reputation']

        try:
            blog_articles = fetch_rss(url, name, reputation, 'article')
            accepted = 0

            for article in blog_articles:
                title = article['title']
                desc = article.get('description', '')

                if is_newsworthy(title, desc):
                    article['category'] = classify_category(title, desc)
                    article['content_type'] = article['category']
                    articles.append(article)
                    accepted += 1
                    print(f"  ✓ {name}: {title[:50]}...")

            if accepted == 0:
                print(f"  - {name}: No newsworthy content")

        except Exception as e:
            print(f"  ⚠ {name}: {e}")

    print(f"  → Found {len(articles)} newsworthy blog posts")
    return articles


def fetch_twitter_posts(config):
    """
    Fetch recent posts from curated AI builder Twitter accounts.
    Uses Nitter RSS feeds as a free alternative to Twitter API.
    Falls back to empty list if Nitter instances are down.
    """
    print("\n🐦 Fetching X/Twitter posts from AI builders...")
    posts = []

    accounts = config['sources'].get('twitter_accounts', [])
    nitter_instances = config['sources'].get('nitter_instances', [
        'https://nitter.poast.org',
        'https://nitter.privacydev.net'
    ])

    for account in accounts:
        handle = account['handle']
        name = account['name']
        reputation = account['reputation']
        focus = account.get('focus', '')

        # Try each Nitter instance until one works
        fetched = False
        for instance in nitter_instances:
            if fetched:
                break

            rss_url = f"{instance}/{handle}/rss"

            try:
                req = urllib.request.Request(rss_url, headers={
                    'User-Agent': 'Mozilla/5.0 AI-Venture-Digest/2.0'
                })
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read().decode('utf-8', errors='ignore')

                root = ET.fromstring(content)
                items = root.findall('.//item')

                for item in items[:3]:  # Max 3 posts per account
                    title = item.findtext('title') or ''
                    link = item.findtext('link') or ''
                    pub_date = item.findtext('pubDate') or ''
                    description = item.findtext('description') or ''

                    # Clean up description (remove HTML)
                    description = re.sub(r'<[^>]+>', '', description)
                    description = html.unescape(description)[:280]

                    # Skip retweets unless they add value
                    if title.startswith('RT by'):
                        continue

                    # Filter for AI-related content
                    text = (title + ' ' + description).lower()
                    ai_keywords = ['ai', 'llm', 'gpt', 'claude', 'cursor', 'agent', 'prompt',
                                   'langchain', 'rag', 'embedding', 'automation', 'workflow',
                                   'saas', 'build', 'ship', 'tool', 'coding', 'dev']

                    if not any(kw in text for kw in ai_keywords):
                        continue

                    if title and link:
                        posts.append({
                            'title': title[:200],
                            'url': link.replace(instance, 'https://x.com'),  # Convert to X URL
                            'description': description,
                            'source': f"@{handle}",
                            'author': name,
                            'reputation': reputation,
                            'published': pub_date,
                            'content_type': 'twitter',
                            'category': 'twitter',
                            'focus': focus,
                            'fetched_at': datetime.now().isoformat()
                        })

                fetched = True
                print(f"  ✓ @{handle}: {len([p for p in posts if p['source'] == f'@{handle}'])} posts")

            except Exception as e:
                continue  # Try next Nitter instance

        if not fetched:
            print(f"  ⚠ @{handle}: Could not fetch (Nitter down)")

    print(f"  → Found {len(posts)} relevant X posts")
    return posts


def fetch_producthunt(config):
    """Fetch AI product launches from Product Hunt."""
    print("\n🚀 Fetching Product Hunt launches...")
    launches = []

    sources = config['sources'].get('producthunt', [])

    for source in sources:
        name = source['name']
        url = source['url']
        reputation = source['reputation']

        try:
            items = fetch_rss(url, name, reputation, 'product_launch')
            accepted = 0

            for item in items:
                title = item['title']
                desc = item.get('description', '')
                text = (title + ' ' + desc).lower()

                # AI keyword filter (word-boundary-safe)
                ai_keywords = [
                    ' ai ', ' ai-', 'gpt', 'llm', 'automation',
                    'no-code', 'copilot', 'agent', 'chatbot',
                ]

                if any(kw in f' {text} ' for kw in ai_keywords):
                    item['category'] = 'launches'
                    item['content_type'] = 'launches'
                    launches.append(item)
                    accepted += 1
                    print(f"  ✓ {name}: {title[:50]}...")

            if accepted == 0:
                print(f"  - {name}: No AI launches found")

        except Exception as e:
            print(f"  ⚠ {name}: {e}")

    print(f"  → Found {len(launches)} AI product launches")
    return launches


def get_top_twitter_posts(posts, limit=5):
    """Select the most relevant Twitter posts for display."""
    if not posts:
        return get_default_twitter_posts()

    # Score posts by recency and reputation
    scored = []
    for post in posts:
        score = post.get('reputation', 0.5)

        # Bonus for actionable content
        text = (post.get('title', '') + ' ' + post.get('description', '')).lower()
        if any(kw in text for kw in ['build', 'ship', 'tutorial', 'how to', 'just launched']):
            score += 0.2

        scored.append((score, post))

    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]


def get_default_twitter_posts():
    """Fallback Twitter posts if fetching fails."""
    return [
        {
            'title': 'The best AI coding tools in 2026: A comparison',
            'url': 'https://x.com/swyx',
            'description': 'Cursor vs Windsurf vs Claude Code - which one fits your workflow?',
            'source': '@swyx',
            'author': 'swyx (Latent Space)',
            'category': 'twitter'
        },
        {
            'title': 'Just shipped a new feature using Claude Code in 2 hours',
            'url': 'https://x.com/levelsio',
            'description': 'The prompting patterns that actually work for production code.',
            'source': '@levelsio',
            'author': 'Pieter Levels',
            'category': 'twitter'
        },
        {
            'title': 'New LangGraph features for multi-agent systems',
            'url': 'https://x.com/LangChainAI',
            'description': 'Check out the latest updates for building agent workflows.',
            'source': '@LangChainAI',
            'author': 'LangChain',
            'category': 'twitter'
        }
    ]


# ============================================================
# SCORING & CATEGORIZATION
# ============================================================

def calculate_score(article, config):
    """Calculate article score favoring actionable content."""
    score = 0
    topics = config.get('topics', [])
    filters = config['filters']

    # Base reputation
    score += article.get('reputation', 0.5) * filters['reputation_weight']

    # Topic relevance
    text = (article.get('title', '') + ' ' + article.get('description', '')).lower()
    matches = sum(1 for topic in topics if topic in text)
    relevance = min(matches / 3, 1.0)
    score += relevance * filters['relevance_weight']

    # Significance bonus — news importance signals
    significance_keywords = [
        'introducing', 'now available', 'generally available', 'launches',
        'launched', 'acquires', 'acquisition', 'partnership',
        'new model', 'release', 'unveils',
    ]
    if any(kw in text for kw in significance_keywords) or re.search(r'\b(raises|raised)\b', text):
        score += 0.15

    # Recency
    try:
        pub_date = article.get('published', '')
        if pub_date:
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S%z', '%a, %d %b %Y %H:%M:%S GMT']:
                try:
                    parsed = datetime.strptime(pub_date.replace('Z', '+0000'), fmt)
                    age_hours = (datetime.now(parsed.tzinfo) - parsed).total_seconds() / 3600
                    recency = max(0, 1 - (age_hours / filters['max_age_hours']))
                    score += recency * filters['recency_weight']
                    break
                except:
                    pass
    except:
        score += 0.3 * filters['recency_weight']

    return score


def get_featured_podcast(podcasts):
    """Select the best podcast episode for today."""
    if not podcasts:
        return None

    # Prefer recent, high-reputation podcasts
    sorted_pods = sorted(podcasts, key=lambda x: x.get('score', 0), reverse=True)
    return sorted_pods[0] if sorted_pods else None


# ============================================================
# DEDUP HISTORY
# ============================================================

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
    num_pruned = len(seen) - len(pruned)
    with open('data/seen_urls.json', 'w') as f:
        json.dump(pruned, f, indent=2)
    return num_pruned


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("🚀 AI Venture Digest - News Fetcher v2.1")
    print("   The AI news that matters")
    print("=" * 60)

    config = load_config()
    seen = load_seen_urls()
    all_articles = []

    # 1. YouTube videos (via Data API v3 search)
    videos = fetch_youtube_search(config)
    all_articles.extend(videos)

    # 2. Podcasts
    podcasts = fetch_podcasts(config)
    all_articles.extend(podcasts)

    # 3. Engineering blogs
    blogs = fetch_engineering_blogs(config)
    all_articles.extend(blogs)

    # 5. Twitter/X posts from AI builders
    twitter_posts = fetch_twitter_posts(config)
    all_articles.extend(twitter_posts)

    # 6. Product Hunt launches
    ph_launches = fetch_producthunt(config)
    all_articles.extend(ph_launches)

    # Score all articles
    print("\n📊 Scoring content...")
    for article in all_articles:
        article['score'] = calculate_score(article, config)

    # Deduplicate against history
    before_dedup = len(all_articles)
    all_articles = [
        a for a in all_articles
        if a['url'] not in seen
    ]
    blocked = before_dedup - len(all_articles)
    if blocked:
        print(f"\n🔁 Dedup: blocked {blocked} previously shown articles ({len(seen)} URLs in history)")
    else:
        print(f"\n🔁 Dedup: no duplicates found ({len(seen)} URLs in history)")

    # Sort by score
    all_articles.sort(key=lambda x: x['score'], reverse=True)

    # Cap articles per source for diversity
    max_per_source = config['filters'].get('max_per_source', 3)
    source_caps = config['filters'].get('source_caps', {})
    source_counts = {}
    diverse_articles = []
    for article in all_articles:
        src = article.get('source', 'unknown')
        cap = source_caps.get(src, max_per_source)
        source_counts[src] = source_counts.get(src, 0) + 1
        if source_counts[src] <= cap:
            diverse_articles.append(article)
    print(f"\n🎯 Source diversity: capped at {max_per_source} per source ({len(all_articles)} → {len(diverse_articles)} articles)")
    all_articles = diverse_articles

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Get featured podcast
    featured_podcast = get_featured_podcast(podcasts)
    if featured_podcast:
        print(f"  → Featured podcast: {featured_podcast['title'][:50]}...")

    # Get top Twitter posts
    top_twitter = get_top_twitter_posts(twitter_posts, limit=5)
    print(f"  → Top {len(top_twitter)} Twitter posts selected")

    # Summary
    categories = {}
    for a in all_articles:
        cat = a.get('category', 'other')
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n📈 Content summary:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  - {cat}: {count}")

    # Limit articles
    max_articles = config['filters'].get('max_articles', 30)
    all_articles = all_articles[:max_articles]

    # Save output
    output = {
        'generated_at': datetime.now().isoformat(),
        'article_count': len(all_articles),
        'featured_podcast': featured_podcast,
        'twitter_posts': top_twitter,
        'categories': categories,
        'youtube_search_queries': config.get('youtube_search_queries', []),
        'articles': all_articles
    }

    os.makedirs('data', exist_ok=True)
    with open('data/articles.json', 'w') as f:
        json.dump(output, f, indent=2)

    # Save dated snapshot for archive
    os.makedirs('data/archive', exist_ok=True)
    archive_date = datetime.now().strftime('%Y-%m-%d')
    archive_path = f'data/archive/{archive_date}.json'
    with open(archive_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"📦 Saved archive snapshot to {archive_path}")

    # Record shown URLs in history for cross-day dedup
    for article in output.get('articles', []):
        seen[article['url']] = today
    if output.get('featured_podcast'):
        seen[output['featured_podcast']['url']] = today
    for tweet in output.get('twitter_posts', []):
        if tweet.get('url', '').startswith('https://x.com/') and '/' in tweet['url'].split('x.com/')[1]:
            # Only record specific tweet URLs, not generic profile fallbacks
            seen[tweet['url']] = today

    archive_days = config.get('output', {}).get('archive_days', 30)
    num_pruned = save_seen_urls(seen, archive_days)
    if num_pruned:
        print(f"🔁 Dedup: pruned {num_pruned} entries older than {archive_days} days")

    print(f"\n💾 Saved {len(all_articles)} articles to data/articles.json")
    print(f"   - {len(podcasts)} podcast episodes")
    print(f"   - {len(top_twitter)} Twitter posts")
    print("✅ Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
