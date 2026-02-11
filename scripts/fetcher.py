#!/usr/bin/env python3
"""
AI Venture Digest - Content Fetcher & Curator
Fetches content from multiple sources and curates based on quality filters.
"""

import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import ssl
import time

# Configuration
CONFIG_PATH = Path(__file__).parent.parent / "config.json"
DATA_PATH = Path(__file__).parent.parent / "data"


@dataclass
class Article:
    id: str
    title: str
    summary: str
    url: str
    source: str
    category: str
    score: float
    engagement: int
    publishedAt: str
    keywords_matched: list


def load_config() -> dict:
    """Load configuration from JSON file."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def generate_id(url: str) -> str:
    """Generate unique ID from URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def fetch_url(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch URL content with error handling."""
    try:
        # Create SSL context that doesn't verify (for simplicity)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'AI-Venture-Digest/1.0 (Content Aggregator)'}
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  ⚠️  Failed to fetch {url}: {e}")
        return None


def parse_rss_feed(content: str, source_name: str, category: str, reputation: float) -> list[Article]:
    """Parse RSS/Atom feed and extract articles."""
    articles = []

    try:
        root = ET.fromstring(content)

        # Handle different feed formats
        items = root.findall('.//item')  # RSS
        if not items:
            # Atom format
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            items = root.findall('.//atom:entry', ns)
            if not items:
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')

        for item in items[:20]:  # Limit to 20 items per feed
            # Extract title
            title_el = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
            title = title_el.text if title_el is not None and title_el.text else ''

            # Extract link
            link_el = item.find('link')
            if link_el is not None:
                link = link_el.text if link_el.text else link_el.get('href', '')
            else:
                link_el = item.find('{http://www.w3.org/2005/Atom}link')
                link = link_el.get('href', '') if link_el is not None else ''

            # Extract description/summary
            desc_el = (item.find('description') or
                      item.find('summary') or
                      item.find('{http://www.w3.org/2005/Atom}summary') or
                      item.find('{http://www.w3.org/2005/Atom}content'))
            description = desc_el.text if desc_el is not None and desc_el.text else ''

            # Clean HTML from description
            description = re.sub(r'<[^>]+>', '', description)
            description = description[:300] + '...' if len(description) > 300 else description

            # Extract date
            date_el = (item.find('pubDate') or
                      item.find('published') or
                      item.find('{http://www.w3.org/2005/Atom}published') or
                      item.find('{http://www.w3.org/2005/Atom}updated'))
            pub_date = parse_date(date_el.text if date_el is not None else None)

            if title and link:
                articles.append(Article(
                    id=generate_id(link),
                    title=title.strip(),
                    summary=description.strip(),
                    url=link.strip(),
                    source=source_name,
                    category=category,
                    score=reputation * 100,  # Base score from reputation
                    engagement=0,
                    publishedAt=pub_date,
                    keywords_matched=[]
                ))
    except ET.ParseError as e:
        print(f"  ⚠️  Failed to parse feed: {e}")

    return articles


def parse_date(date_str: Optional[str]) -> str:
    """Parse various date formats to ISO format."""
    if not date_str:
        return datetime.now().isoformat()

    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]

    # Clean up the date string
    date_str = date_str.strip()

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.isoformat()
        except ValueError:
            continue

    return datetime.now().isoformat()


def fetch_hackernews(config: dict) -> list[Article]:
    """Fetch top stories from Hacker News."""
    articles = []
    hn_config = config['sources']['hackernews']

    if not hn_config.get('enabled', False):
        return articles

    print("📡 Fetching Hacker News...")

    # Get top stories
    content = fetch_url('https://hacker-news.firebaseio.com/v0/topstories.json')
    if not content:
        return articles

    try:
        story_ids = json.loads(content)[:50]  # Top 50 stories
    except json.JSONDecodeError:
        return articles

    keywords = [k.lower() for k in hn_config.get('keywords', [])]
    min_score = hn_config.get('min_score', 50)

    for story_id in story_ids:
        story_content = fetch_url(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json')
        if not story_content:
            continue

        try:
            story = json.loads(story_content)
        except json.JSONDecodeError:
            continue

        if story.get('type') != 'story':
            continue

        title = story.get('title', '')
        score = story.get('score', 0)

        # Check if it matches keywords and minimum score
        title_lower = title.lower()
        matched_keywords = [k for k in keywords if k in title_lower]

        if matched_keywords and score >= min_score:
            url = story.get('url', f"https://news.ycombinator.com/item?id={story_id}")

            articles.append(Article(
                id=generate_id(url),
                title=title,
                summary=f"Discussed on Hacker News with {story.get('descendants', 0)} comments.",
                url=url,
                source='Hacker News',
                category='news',
                score=min(score / 5, 100),  # Normalize score
                engagement=score,
                publishedAt=datetime.fromtimestamp(story.get('time', 0)).isoformat(),
                keywords_matched=matched_keywords
            ))

        time.sleep(0.1)  # Rate limiting

    print(f"  ✓ Found {len(articles)} relevant HN stories")
    return articles


def fetch_reddit(config: dict) -> list[Article]:
    """Fetch posts from Reddit."""
    articles = []
    reddit_config = config['sources']['reddit']

    if not reddit_config.get('enabled', False):
        return articles

    print("📡 Fetching Reddit...")

    min_score = reddit_config.get('min_score', 100)

    for subreddit in reddit_config.get('subreddits', []):
        url = f'https://www.reddit.com/r/{subreddit}/hot.json?limit=25'
        content = fetch_url(url)

        if not content:
            continue

        try:
            data = json.loads(content)
            posts = data.get('data', {}).get('children', [])
        except json.JSONDecodeError:
            continue

        for post in posts:
            post_data = post.get('data', {})
            score = post_data.get('score', 0)

            if score < min_score:
                continue

            title = post_data.get('title', '')
            post_url = post_data.get('url', '')
            permalink = f"https://reddit.com{post_data.get('permalink', '')}"

            articles.append(Article(
                id=generate_id(permalink),
                title=title,
                summary=f"From r/{subreddit} • {post_data.get('num_comments', 0)} comments",
                url=post_url if not post_url.startswith('/r/') else permalink,
                source=f'r/{subreddit}',
                category='news',
                score=min(score / 10, 100),
                engagement=score,
                publishedAt=datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                keywords_matched=[]
            ))

        time.sleep(1)  # Reddit rate limiting

    print(f"  ✓ Found {len(articles)} Reddit posts")
    return articles


def calculate_relevance_score(article: Article, topics: dict) -> tuple[float, list[str]]:
    """Calculate relevance score based on keyword matching."""
    text = (article.title + ' ' + article.summary).lower()

    primary_matches = [k for k in topics.get('primary', []) if k.lower() in text]
    secondary_matches = [k for k in topics.get('secondary', []) if k.lower() in text]
    example_matches = [k for k in topics.get('examples', []) if k.lower() in text]

    # Weight: primary=1.0, secondary=0.5, examples=0.75
    score = (
        len(primary_matches) * 1.0 +
        len(secondary_matches) * 0.5 +
        len(example_matches) * 0.75
    )

    all_matches = primary_matches + secondary_matches + example_matches

    # Normalize to 0-1 range
    normalized_score = min(score / 3, 1.0)

    return normalized_score, all_matches


def curate_articles(articles: list[Article], config: dict) -> list[Article]:
    """Apply curation filters and calculate final scores."""
    print("\n🎯 Curating articles...")

    filters = config['filters']
    topics = config['topics']
    curation = config['curation']
    max_age_hours = filters['recency'].get('max_age_hours', 48)

    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    curated = []

    for article in articles:
        # Check recency
        try:
            pub_date = datetime.fromisoformat(article.publishedAt.replace('Z', '+00:00').replace('+00:00', ''))
        except:
            pub_date = datetime.now()

        if pub_date.replace(tzinfo=None) < cutoff_time:
            continue

        # Calculate relevance
        relevance_score, matched_keywords = calculate_relevance_score(article, topics)
        article.keywords_matched = matched_keywords

        # Skip if no relevance and minimum required
        if filters['relevance']['enabled'] and relevance_score == 0:
            if filters['relevance'].get('min_keyword_matches', 0) > 0:
                continue

        # Calculate weighted final score
        weights = {
            'engagement': filters['engagement'].get('weight', 0.3),
            'reputation': filters['reputation'].get('weight', 0.25),
            'recency': filters['recency'].get('weight', 0.2),
            'relevance': filters['relevance'].get('weight', 0.25),
        }

        # Normalize engagement (assuming max ~1000)
        engagement_score = min(article.engagement / 1000, 1.0) if article.engagement else 0.5

        # Reputation is already in base score (0-100)
        reputation_score = article.score / 100

        # Recency score (newer = higher)
        hours_old = (datetime.now() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
        recency_score = max(0, 1 - (hours_old / max_age_hours))

        final_score = (
            engagement_score * weights['engagement'] +
            reputation_score * weights['reputation'] +
            recency_score * weights['recency'] +
            relevance_score * weights['relevance']
        ) * 100

        # Apply minimum threshold
        if final_score < curation.get('min_total_score', 0.5) * 100:
            continue

        article.score = round(final_score)
        curated.append(article)

    # Sort by score and limit
    curated.sort(key=lambda x: x.score, reverse=True)
    max_items = curation.get('max_items_per_day', 20)

    print(f"  ✓ Curated {len(curated[:max_items])} articles from {len(articles)} total")

    return curated[:max_items]


def detect_category(article: Article, topics: dict) -> str:
    """Detect the best category for an article based on content."""
    text = (article.title + ' ' + article.summary).lower()

    # Category keywords
    category_signals = {
        'tools': ['tool', 'api', 'sdk', 'library', 'framework', 'release', 'launch', 'update', 'version'],
        'research': ['paper', 'arxiv', 'study', 'research', 'findings', 'discovered', 'breakthrough'],
        'examples': ['how to', 'tutorial', 'guide', 'case study', 'example', 'built', 'implementation', 'workflow'],
        'business': ['funding', 'startup', 'investment', 'valuation', 'acquisition', 'enterprise', 'market'],
    }

    # Check for example keywords (high priority for venture builders)
    if any(k in text for k in topics.get('examples', [])):
        return 'examples'

    # Count signals for each category
    scores = {}
    for category, signals in category_signals.items():
        scores[category] = sum(1 for s in signals if s in text)

    if max(scores.values()) > 0:
        return max(scores, key=scores.get)

    return article.category  # Keep original if no better match


def save_articles(articles: list[Article], config: dict):
    """Save articles to JSON file."""
    DATA_PATH.mkdir(exist_ok=True)

    output_file = DATA_PATH / 'articles.json'

    # Convert to dict
    articles_data = {
        'lastUpdated': datetime.now().isoformat(),
        'count': len(articles),
        'articles': [asdict(a) for a in articles]
    }

    with open(output_file, 'w') as f:
        json.dump(articles_data, f, indent=2)

    print(f"\n💾 Saved {len(articles)} articles to {output_file}")

    # Also save archive
    archive_file = DATA_PATH / f'archive_{datetime.now().strftime("%Y%m%d")}.json'
    with open(archive_file, 'w') as f:
        json.dump(articles_data, f, indent=2)


def main():
    """Main execution flow."""
    print("=" * 50)
    print("🚀 AI Venture Digest - Content Fetcher")
    print("=" * 50)
    print()

    # Load config
    config = load_config()
    all_articles = []

    # Fetch RSS feeds
    print("📡 Fetching RSS feeds...")
    for feed in config['sources']['rss_feeds']:
        print(f"  → {feed['name']}")
        content = fetch_url(feed['url'])
        if content:
            articles = parse_rss_feed(
                content,
                feed['name'],
                feed['category'],
                feed['reputation']
            )
            all_articles.extend(articles)
            print(f"    ✓ {len(articles)} articles")
        time.sleep(0.5)

    # Fetch Hacker News
    hn_articles = fetch_hackernews(config)
    all_articles.extend(hn_articles)

    # Fetch Reddit
    reddit_articles = fetch_reddit(config)
    all_articles.extend(reddit_articles)

    # Deduplicate by URL
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article.url not in seen_urls:
            seen_urls.add(article.url)
            # Re-detect category
            article.category = detect_category(article, config['topics'])
            unique_articles.append(article)

    print(f"\n📊 Total unique articles: {len(unique_articles)}")

    # Curate
    curated = curate_articles(unique_articles, config)

    # Save
    save_articles(curated, config)

    print("\n✅ Done!")
    print("=" * 50)


if __name__ == '__main__':
    main()
