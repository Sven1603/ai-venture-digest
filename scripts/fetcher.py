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


def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)


# ============================================================
# STRICT CONTENT FILTERS
# These are the gatekeepers - be VERY selective
# ============================================================

def is_actionable_content(title, description=''):
    """
    STRICT filter: Is this content actionable for a venture builder?
    Must teach HOW to do something, not just announce news.
    """
    text = (title + ' ' + description).lower()

    # MUST have actionable indicators
    actionable_keywords = [
        'how to', 'tutorial', 'build', 'create', 'step by step', 'guide',
        'in 5 min', 'in 10 min', 'in 15 min', 'in 30 min', 'from scratch',
        'complete guide', 'hands-on', 'walkthrough', 'implement', 'setup',
        'integrate', 'automate', 'workflow', 'template', 'boilerplate',
        'quickstart', 'getting started', 'beginner', 'practical',
        'i built', 'let\'s build', 'building a', 'making a', 'code along',
        'full stack', 'saas', 'mvp', 'launch', 'ship'
    ]

    # HARD EXCLUDE - these never pass
    hard_exclude = [
        # Nature/wildlife (wrong channel content)
        'anaconda', 'jungle', 'amazon rainforest', 'wildlife', 'animal', 'snake',
        'nature documentary', 'expedition', 'tribe', 'predator', 'prey',
        # Academic papers (not actionable)
        'paper analysis', 'paper review', 'arxiv', 'research paper',
        'variational autoencoder', 'theoretical', 'proof that',
        # Pure news/announcements
        'breaking:', 'just announced', 'exclusive:', 'leaked',
        'drama', 'controversy', 'beef', 'drama between',
        # Funding/business news
        'raises $', 'raised $', 'funding round', 'valuation', 'ipo',
        'acquires', 'acquisition', 'layoffs', 'laid off',
        'series a', 'series b', 'seed round',
        # General news format
        'weekly roundup', 'news recap', 'this week in', 'weekly digest',
        "what's new in", 'announcing', 'we\'re excited to announce'
    ]

    # Soft exclude - can pass if also has actionable keywords
    soft_exclude = [
        'news', 'announcement', 'update', 'reaction', 'thoughts on',
        'my opinion', 'review', 'first look', 'impressions',
        'interview', 'podcast', 'discussion'  # podcasts handled separately
    ]

    # Hard exclude always fails
    if any(kw in text for kw in hard_exclude):
        return False

    # Check actionable
    has_actionable = any(kw in text for kw in actionable_keywords)
    has_soft_exclude = any(kw in text for kw in soft_exclude)

    # If has actionable keywords and no soft exclude, pass
    if has_actionable and not has_soft_exclude:
        return True

    # If has actionable AND soft exclude, only pass if actionable is strong
    strong_actionable = ['how to', 'tutorial', 'step by step', 'build', 'from scratch', 'code along']
    if has_actionable and has_soft_exclude:
        return any(kw in text for kw in strong_actionable)

    return False


def is_tool_content(title, description=''):
    """Check if content is about a specific AI tool that builders can use."""
    text = (title + ' ' + description).lower()

    tool_keywords = [
        'cursor', 'claude', 'claude code', 'chatgpt', 'gpt-4', 'gpt-5',
        'copilot', 'v0', 'bolt', 'lovable', 'replit', 'windsurf',
        'langchain', 'langgraph', 'llamaindex', 'autogen', 'crewai',
        'n8n', 'make.com', 'zapier', 'dify', 'flowise', 'langflow',
        'remotion', 'elevenlabs', 'runway', 'midjourney', 'stable diffusion',
        'perplexity', 'phind', 'gemini', 'anthropic', 'openai api',
        'supabase', 'vercel', 'netlify', 'railway', 'render'
    ]

    # Must mention a tool AND be somewhat actionable
    has_tool = any(kw in text for kw in tool_keywords)

    # Exclude pure product announcements
    announcement_words = ['raises', 'funding', 'valuation', 'announces', 'partnership']
    is_announcement = any(w in text for w in announcement_words)

    return has_tool and not is_announcement


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
            description = item.findtext('description') or item.findtext('{http://www.w3.org/2005/Atom}summary') or ''
            pub_date = item.findtext('pubDate') or item.findtext('{http://www.w3.org/2005/Atom}published') or ''

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

def fetch_youtube_tutorials(config):
    """
    Fetch tutorial videos from curated YouTube channels.
    STRICT filtering for actionable content only.
    """
    print("\n🎬 Fetching YouTube tutorials...")
    videos = []

    channels = config['sources'].get('youtube_channels', [])

    for channel in channels:
        name = channel['name']
        channel_id = channel['channel_id']
        reputation = channel['reputation']
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        try:
            channel_videos = fetch_rss(url, name, reputation, 'video')
            accepted = 0

            for video in channel_videos:
                title = video['title']
                desc = video.get('description', '')

                # STRICT filter
                if is_actionable_content(title, desc):
                    video['content_type'] = 'tutorial'
                    video['category'] = 'tutorial'
                    videos.append(video)
                    accepted += 1
                    print(f"  ✓ {name}: {title[:50]}...")
                elif is_tool_content(title, desc):
                    video['content_type'] = 'tool_demo'
                    video['category'] = 'tools'
                    videos.append(video)
                    accepted += 1
                    print(f"  ✓ {name}: {title[:50]}...")

            if accepted == 0:
                print(f"  - {name}: No actionable content found")

        except Exception as e:
            print(f"  ⚠ {name}: {e}")

    print(f"  → Found {len(videos)} actionable tutorial videos")
    return videos


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

                if is_actionable_content(title, desc):
                    article['content_type'] = 'deep_dive'
                    article['category'] = 'deep_dive'
                    articles.append(article)
                    accepted += 1
                    print(f"  ✓ {name}: {title[:50]}...")
                elif is_tool_content(title, desc):
                    article['content_type'] = 'tool_update'
                    article['category'] = 'tools'
                    articles.append(article)
                    accepted += 1
                    print(f"  ✓ {name}: {title[:50]}...")

            if accepted == 0:
                print(f"  - {name}: No actionable content")

        except Exception as e:
            print(f"  ⚠ {name}: {e}")

    print(f"  → Found {len(articles)} actionable blog posts")
    return articles


def get_github_skills(config):
    """
    Get curated Claude Code skills from config.
    These are manually curated, high-quality resources.
    """
    print("\n⚡ Loading curated Claude skills...")
    skills = []

    github_skills = config['sources'].get('github_skills', [])

    for skill in github_skills:
        skills.append({
            'title': skill['name'],
            'url': skill['url'],
            'description': skill['description'],
            'source': 'GitHub',
            'reputation': 0.95,
            'content_type': 'skill',
            'category': 'skill',
            'fetched_at': datetime.now().isoformat()
        })
        print(f"  ✓ {skill['name']}")

    print(f"  → Loaded {len(skills)} curated skills")
    return skills


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

    # Content type bonus
    content_type = article.get('content_type', '')
    type_bonuses = {
        'tutorial': 0.25,
        'deep_dive': 0.20,
        'skill': 0.20,
        'tool_demo': 0.15,
        'tool_update': 0.10,
        'podcast': 0.12
    }
    score += type_bonuses.get(content_type, 0)

    # Strong actionable keywords bonus
    strong_keywords = ['step by step', 'from scratch', 'complete guide', 'hands-on']
    if any(kw in text for kw in strong_keywords):
        score += 0.10

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


# ============================================================
# QUICK WINS GENERATION
# ============================================================

def create_quick_wins(articles, skills):
    """
    Create Quick Wins section:
    1. New Tool - Something to try today
    2. Claude Skill - A skill to install
    3. Quick Tutorial - A fast tutorial to follow
    """
    quick_wins = []

    # 1. Find best new tool
    tools = [a for a in articles if a.get('category') in ['tools'] or a.get('content_type') in ['tool_demo', 'tool_update']]
    if tools:
        tool = max(tools, key=lambda x: x.get('score', 0))
        quick_wins.append({
            'type': 'new_tool',
            'icon': '🆕',
            'label': 'New Tool',
            'title': tool['title'][:80],
            'description': tool.get('description', '')[:120],
            'url': tool['url'],
            'source': tool.get('source', '')
        })

    # 2. Add a Claude skill
    if skills:
        skill = skills[0]
        quick_wins.append({
            'type': 'skill',
            'icon': '⚡',
            'label': 'Claude Skill',
            'title': skill['title'],
            'description': skill.get('description', '')[:120],
            'url': skill['url'],
            'source': 'GitHub'
        })

    # 3. Find quick tutorial (prefer short ones)
    tutorials = [a for a in articles if a.get('category') == 'tutorial' or a.get('content_type') == 'tutorial']
    short_indicators = ['5 min', '10 min', '15 min', 'quick', 'fast', 'simple']
    short_tutorials = [t for t in tutorials if any(x in t.get('title', '').lower() for x in short_indicators)]

    if short_tutorials:
        tut = max(short_tutorials, key=lambda x: x.get('score', 0))
    elif tutorials:
        tut = max(tutorials, key=lambda x: x.get('score', 0))
    else:
        tut = None

    if tut:
        quick_wins.append({
            'type': 'tutorial',
            'icon': '🎯',
            'label': 'Quick Tutorial',
            'title': tut['title'][:80],
            'description': tut.get('description', '')[:120],
            'url': tut['url'],
            'source': tut.get('source', ''),
            'video_url': tut.get('video_url')
        })

    return quick_wins


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
    print("🚀 AI Venture Digest - Actionable Content Fetcher v2.1")
    print("   For Venture Builders Who Ship")
    print("=" * 60)

    config = load_config()
    seen = load_seen_urls()
    all_articles = []

    # 1. YouTube tutorials (strictly filtered)
    videos = fetch_youtube_tutorials(config)
    all_articles.extend(videos)

    # 2. Podcasts
    podcasts = fetch_podcasts(config)
    all_articles.extend(podcasts)

    # 3. Engineering blogs
    blogs = fetch_engineering_blogs(config)
    all_articles.extend(blogs)

    # 4. GitHub skills (curated)
    skills = get_github_skills(config)
    all_articles.extend(skills)

    # 5. Twitter/X posts from AI builders
    twitter_posts = fetch_twitter_posts(config)
    all_articles.extend(twitter_posts)

    # Score all articles
    print("\n📊 Scoring content...")
    for article in all_articles:
        article['score'] = calculate_score(article, config)

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

    # Sort by score
    all_articles.sort(key=lambda x: x['score'], reverse=True)

    # Cap articles per source for diversity
    max_per_source = config['filters'].get('max_per_source', 3)
    source_counts = {}
    diverse_articles = []
    for article in all_articles:
        src = article.get('source', 'unknown')
        source_counts[src] = source_counts.get(src, 0) + 1
        if source_counts[src] <= max_per_source:
            diverse_articles.append(article)
    print(f"\n🎯 Source diversity: capped at {max_per_source} per source ({len(all_articles)} → {len(diverse_articles)} articles)")
    all_articles = diverse_articles

    # Create Quick Wins
    print("\n🎯 Creating Quick Wins...")
    quick_wins = create_quick_wins(all_articles, skills)
    print(f"  → Created {len(quick_wins)} quick wins")

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
        'quick_wins': quick_wins,
        'featured_podcast': featured_podcast,
        'twitter_posts': top_twitter,
        'categories': categories,
        'articles': all_articles
    }

    os.makedirs('data', exist_ok=True)
    with open('data/articles.json', 'w') as f:
        json.dump(output, f, indent=2)

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

    archive_days = config.get('output', {}).get('archive_days', 30)
    num_pruned = save_seen_urls(seen, archive_days)
    if num_pruned:
        print(f"🔁 Dedup: pruned {num_pruned} entries older than {archive_days} days")

    print(f"\n💾 Saved {len(all_articles)} articles to data/articles.json")
    print(f"   - {len(quick_wins)} quick wins")
    print(f"   - {len(podcasts)} podcast episodes")
    print(f"   - {len([a for a in all_articles if a.get('category') == 'tutorial'])} tutorials")
    print(f"   - {len(top_twitter)} Twitter posts")
    print("✅ Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
