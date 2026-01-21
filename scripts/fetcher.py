#!/usr/bin/env python3
"""
AI Venture Digest - Content Fetcher and Curator
Fetches AI news from RSS feeds, extracts thumbnails, and curates content.
"""

import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
import html
import os

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def extract_thumbnail(entry, content=''):
    """Extract thumbnail URL from RSS entry or content."""
    # Check for media:thumbnail
    for child in entry:
        if 'thumbnail' in child.tag.lower():
            url = child.get('url') or child.text
            if url:
                return url
        if 'content' in child.tag.lower() and child.get('url'):
            return child.get('url')
        if 'enclosure' in child.tag.lower():
            enc_type = child.get('type', '')
            if 'image' in enc_type:
                return child.get('url')
    
    # Try to find image in content/description
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
    if img_match:
        return img_match.group(1)
    
    # Check for og:image style URLs in content
    og_match = re.search(r'(https?://[^\s<>"]+\.(?:jpg|jpeg|png|gif|webp))', content, re.I)
    if og_match:
        return og_match.group(1)
    
    return None

def fetch_rss(url, source_name, reputation, is_video=False, is_podcast=False):
    """Fetch and parse RSS feed."""
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 AI-Venture-Digest/1.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8', errors='ignore')
        
        root = ET.fromstring(content)
        
        # Handle both RSS and Atom feeds
        items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
        
        for item in items[:10]:  # Limit per feed
            # RSS format
            title = item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title') or ''
            link = item.findtext('link') or ''
            description = item.findtext('description') or item.findtext('{http://www.w3.org/2005/Atom}summary') or ''
            pub_date = item.findtext('pubDate') or item.findtext('{http://www.w3.org/2005/Atom}published') or ''
            
            # Atom link handling
            if not link:
                link_elem = item.find('{http://www.w3.org/2005/Atom}link')
                if link_elem is not None:
                    link = link_elem.get('href', '')
            
            # Clean HTML from description
            description = re.sub(r'<[^>]+>', '', description)
            description = html.unescape(description)[:300]
            
            # Extract thumbnail
            thumbnail = extract_thumbnail(item, description)
            
            # Detect video URLs
            video_url = None
            if is_video or 'youtube.com' in link or 'youtu.be' in link:
                video_url = link
                # Extract YouTube thumbnail if not found
                yt_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', link)
                if yt_match and not thumbnail:
                    thumbnail = f"https://img.youtube.com/vi/{yt_match.group(1)}/hqdefault.jpg"
            
            # Podcast episode info
            podcast_duration = None
            if is_podcast:
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
                    'is_podcast': is_podcast,
                    'podcast_duration': podcast_duration,
                    'fetched_at': datetime.now().isoformat()
                })
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
    
    return articles

def fetch_youtube_search(query="AI artificial intelligence news"):
    """Fetch latest AI videos from YouTube RSS (via Invidious or similar)."""
    # YouTube doesn't have public RSS for search, so we use curated channels
    youtube_channels = [
        ("Two Minute Papers", "https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg", 0.95),
        ("AI Explained", "https://www.youtube.com/feeds/videos.xml?channel_id=UCNF0LEQ2abMr0PAX3kG6R9Q", 0.9),
        ("Yannic Kilcher", "https://www.youtube.com/feeds/videos.xml?channel_id=UCZHmQk67mSJgfCCTn7xBfew", 0.9),
        ("Matt Wolfe", "https://www.youtube.com/feeds/videos.xml?channel_id=UCJIfeSCssxSC_Dhc5s7woww", 0.85),
        ("The AI Advantage", "https://www.youtube.com/feeds/videos.xml?channel_id=UCmXbMJfGv1xA0wGH5UQ3Ogg", 0.85),
    ]
    
    videos = []
    for name, url, rep in youtube_channels:
        channel_videos = fetch_rss(url, name, rep, is_video=True)
        videos.extend(channel_videos)
    
    return videos

def fetch_podcasts():
    """Fetch AI podcast episodes."""
    podcast_feeds = [
        ("Lex Fridman Podcast", "https://lexfridman.com/feed/podcast/", 0.95),
        ("The AI Podcast (NVIDIA)", "https://feeds.soundcloud.com/users/soundcloud:users:264034133/sounds.rss", 0.9),
        ("Practical AI", "https://changelog.com/practicalai/feed", 0.85),
        ("TWIML AI Podcast", "https://twimlai.com/feed/", 0.85),
    ]
    
    podcasts = []
    for name, url, rep in podcast_feeds:
        episodes = fetch_rss(url, name, rep, is_podcast=True)
        # Filter for AI-related content
        for ep in episodes:
            title_lower = ep['title'].lower()
            if any(kw in title_lower for kw in ['ai', 'artificial', 'machine learning', 'neural', 'gpt', 'llm', 'deep learning', 'robot']):
                podcasts.append(ep)
    
    return podcasts

def calculate_score(article, config):
    """Calculate article score based on weighted factors."""
    score = 0
    weights = config['filters']
    topics = config.get('topics', [])
    
    # Reputation score
    score += article.get('reputation', 0.5) * weights['reputation_weight']
    
    # Relevance score (keyword matching)
    title_lower = article.get('title', '').lower()
    desc_lower = article.get('description', '').lower()
    text = title_lower + ' ' + desc_lower
    
    keyword_matches = sum(1 for topic in topics if topic.lower() in text)
    relevance = min(keyword_matches / 3, 1.0)  # Cap at 1.0
    score += relevance * weights['relevance_weight']
    
    # Recency score
    try:
        pub_date = article.get('published', '')
        if pub_date:
            # Parse various date formats
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S%z', '%a, %d %b %Y %H:%M:%S GMT']:
                try:
                    parsed = datetime.strptime(pub_date.replace('Z', '+0000'), fmt)
                    age_hours = (datetime.now(parsed.tzinfo) - parsed).total_seconds() / 3600
                    recency = max(0, 1 - (age_hours / config['filters']['max_age_hours']))
                    score += recency * weights['recency_weight']
                    break
                except:
                    pass
    except:
        score += 0.3 * weights['recency_weight']  # Default if can't parse
    
    # Engagement placeholder (would need API for real data)
    score += 0.5 * weights['engagement_weight']
    
    return score

def categorize(article):
    """Categorize article by type."""
    title = article.get('title', '').lower()
    desc = article.get('description', '').lower()
    text = title + ' ' + desc
    
    if article.get('video_url'):
        return 'video'
    if article.get('is_podcast'):
        return 'podcast'
    if any(w in text for w in ['tutorial', 'how to', 'guide', 'example', 'code']):
        return 'examples'
    if any(w in text for w in ['tool', 'app', 'platform', 'release', 'launch', 'api']):
        return 'tools'
    if any(w in text for w in ['startup', 'funding', 'acquisition', 'valuation', 'business']):
        return 'business'
    if any(w in text for w in ['research', 'paper', 'study', 'arxiv', 'findings']):
        return 'research'
    return 'news'

def main():
    print("Starting AI Venture Digest fetch...")
    config = load_config()
    all_articles = []
    
    # Fetch from RSS feeds
    print("Fetching RSS feeds...")
    for feed in config['sources']['rss_feeds']:
        print(f"  - {feed['name']}")
        articles = fetch_rss(feed['url'], feed['name'], feed['reputation'])
        all_articles.extend(articles)
    
    # Fetch YouTube videos
    print("Fetching YouTube videos...")
    videos = fetch_youtube_search()
    all_articles.extend(videos)
    print(f"  Found {len(videos)} videos")
    
    # Fetch podcasts
    print("Fetching podcasts...")
    podcasts = fetch_podcasts()
    all_articles.extend(podcasts)
    print(f"  Found {len(podcasts)} podcast episodes")
    
    # Score and categorize
    print("Scoring and categorizing articles...")
    for article in all_articles:
        article['score'] = calculate_score(article, config)
        article['category'] = categorize(article)
    
    # Sort by score
    all_articles.sort(key=lambda x: x['score'], reverse=True)
    
    # Ensure we have at least one video
    videos_in_list = [a for a in all_articles if a['category'] == 'video']
    if not videos_in_list:
        print("Warning: No videos found, adding fallback...")
        # This shouldn't happen with YouTube feeds, but just in case
    
    # Ensure we have podcasts
    podcasts_in_list = [a for a in all_articles if a['category'] == 'podcast']
    print(f"Podcasts in final list: {len(podcasts_in_list)}")
    
    # Limit total articles
    all_articles = all_articles[:config['filters']['max_articles']]
    
    # Save to JSON
    output = {
        'generated_at': datetime.now().isoformat(),
        'article_count': len(all_articles),
        'video_count': len([a for a in all_articles if a['category'] == 'video']),
        'podcast_count': len([a for a in all_articles if a['category'] == 'podcast']),
        'articles': all_articles
    }
    
    os.makedirs('data', exist_ok=True)
    with open('data/articles.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Saved {len(all_articles)} articles to data/articles.json")
    print(f"  - Videos: {output['video_count']}")
    print(f"  - Podcasts: {output['podcast_count']}")

if __name__ == '__main__':
    main()
