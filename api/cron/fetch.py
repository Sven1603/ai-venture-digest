"""
Vercel Cron Job: Fetch and curate AI news daily
Runs at 7 AM UTC via Vercel Cron
"""

import json
import hashlib
import re
import os
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import ssl
import time
import base64


# ============ CONFIGURATION ============

CONFIG = {
    "topics": {
        "primary": ["generative AI", "LLM", "AI tools", "AI APIs", "coding assistants", "AI automation"],
        "secondary": ["startup", "product launch", "go-to-market", "AI business", "venture", "MVP"],
        "examples": ["use case", "tutorial", "how to", "case study", "implementation", "workflow"]
    },
    "sources": {
        "rss_feeds": [
            {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "news", "reputation": 0.9},
            {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "category": "news", "reputation": 0.85},
            {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "category": "news", "reputation": 0.9},
            {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "category": "news", "reputation": 0.95},
            {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "category": "research", "reputation": 1.0},
            {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "category": "research", "reputation": 1.0},
            {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "category": "tools", "reputation": 0.95},
            {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "category": "tools", "reputation": 0.9}
        ],
        "hackernews": {
            "min_score": 50,
            "keywords": ["AI", "GPT", "LLM", "Claude", "OpenAI", "Anthropic", "machine learning", "generative"],
            "enabled": True
        },
        "reddit": {
            "subreddits": ["MachineLearning", "artificial", "ChatGPT", "LocalLLaMA"],
            "min_score": 100,
            "enabled": True
        }
    },
    "filters": {
        "max_age_hours": 48,
        "min_total_score": 50,
        "max_items": 20
    }
}


# ============ FETCHER LOGIC ============

def generate_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def fetch_url(url: str, timeout: int = 15) -> str | None:
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'AI-Venture-Digest/1.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None


def parse_date(date_str: str | None) -> str:
    if not date_str:
        return datetime.now().isoformat()
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).isoformat()
        except ValueError:
            continue
    return datetime.now().isoformat()


def parse_rss_feed(content: str, source_name: str, category: str, reputation: float) -> list[dict]:
    articles = []
    try:
        root = ET.fromstring(content)
        items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

        for item in items[:15]:
            title_el = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
            title = title_el.text if title_el is not None and title_el.text else ''

            link_el = item.find('link')
            if link_el is not None:
                link = link_el.text if link_el.text else link_el.get('href', '')
            else:
                link_el = item.find('{http://www.w3.org/2005/Atom}link')
                link = link_el.get('href', '') if link_el is not None else ''

            desc_el = item.find('description') or item.find('{http://www.w3.org/2005/Atom}summary')
            description = desc_el.text if desc_el is not None and desc_el.text else ''
            description = re.sub(r'<[^>]+>', '', description)[:300]

            date_el = item.find('pubDate') or item.find('{http://www.w3.org/2005/Atom}published')
            pub_date = parse_date(date_el.text if date_el is not None else None)

            if title and link:
                articles.append({
                    "id": generate_id(link),
                    "title": title.strip(),
                    "summary": description.strip(),
                    "url": link.strip(),
                    "source": source_name,
                    "category": category,
                    "score": reputation * 100,
                    "engagement": 0,
                    "publishedAt": pub_date,
                    "keywords_matched": []
                })
    except ET.ParseError as e:
        print(f"Failed to parse RSS: {e}")
    return articles


def fetch_hackernews() -> list[dict]:
    articles = []
    hn_config = CONFIG['sources']['hackernews']
    if not hn_config.get('enabled'):
        return articles

    content = fetch_url('https://hacker-news.firebaseio.com/v0/topstories.json')
    if not content:
        return articles

    try:
        story_ids = json.loads(content)[:30]
    except json.JSONDecodeError:
        return articles

    keywords = [k.lower() for k in hn_config.get('keywords', [])]
    min_score = hn_config.get('min_score', 50)

    for story_id in story_ids[:20]:
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
        title_lower = title.lower()
        matched = [k for k in keywords if k in title_lower]

        if matched and score >= min_score:
            url = story.get('url', f"https://news.ycombinator.com/item?id={story_id}")
            articles.append({
                "id": generate_id(url),
                "title": title,
                "summary": f"Discussed on Hacker News with {story.get('descendants', 0)} comments.",
                "url": url,
                "source": "Hacker News",
                "category": "news",
                "score": min(score / 5, 100),
                "engagement": score,
                "publishedAt": datetime.fromtimestamp(story.get('time', 0)).isoformat(),
                "keywords_matched": matched
            })
        time.sleep(0.1)

    return articles


def fetch_reddit() -> list[dict]:
    articles = []
    reddit_config = CONFIG['sources']['reddit']
    if not reddit_config.get('enabled'):
        return articles

    min_score = reddit_config.get('min_score', 100)

    for subreddit in reddit_config.get('subreddits', [])[:3]:
        content = fetch_url(f'https://www.reddit.com/r/{subreddit}/hot.json?limit=15')
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
            permalink = f"https://reddit.com{post_data.get('permalink', '')}"
            post_url = post_data.get('url', permalink)

            articles.append({
                "id": generate_id(permalink),
                "title": title,
                "summary": f"From r/{subreddit} • {post_data.get('num_comments', 0)} comments",
                "url": post_url if not post_url.startswith('/r/') else permalink,
                "source": f"r/{subreddit}",
                "category": "news",
                "score": min(score / 10, 100),
                "engagement": score,
                "publishedAt": datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                "keywords_matched": []
            })
        time.sleep(1)

    return articles


def calculate_relevance(article: dict, topics: dict) -> tuple[float, list[str]]:
    text = (article['title'] + ' ' + article['summary']).lower()
    primary = [k for k in topics.get('primary', []) if k.lower() in text]
    secondary = [k for k in topics.get('secondary', []) if k.lower() in text]
    examples = [k for k in topics.get('examples', []) if k.lower() in text]
    score = len(primary) * 1.0 + len(secondary) * 0.5 + len(examples) * 0.75
    return min(score / 3, 1.0), primary + secondary + examples


def detect_category(article: dict, topics: dict) -> str:
    text = (article['title'] + ' ' + article['summary']).lower()
    if any(k in text for k in topics.get('examples', [])):
        return 'examples'
    signals = {
        'tools': ['tool', 'api', 'sdk', 'library', 'framework', 'release', 'launch'],
        'research': ['paper', 'arxiv', 'study', 'research', 'findings', 'breakthrough'],
        'examples': ['how to', 'tutorial', 'guide', 'case study', 'built'],
        'business': ['funding', 'startup', 'investment', 'valuation', 'acquisition'],
    }
    scores = {cat: sum(1 for s in sigs if s in text) for cat, sigs in signals.items()}
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return article['category']


def curate_articles(articles: list[dict]) -> list[dict]:
    topics = CONFIG['topics']
    filters = CONFIG['filters']
    cutoff = datetime.now() - timedelta(hours=filters['max_age_hours'])
    curated = []

    for article in articles:
        try:
            pub_date = datetime.fromisoformat(article['publishedAt'].replace('Z', ''))
        except:
            pub_date = datetime.now()

        if pub_date < cutoff:
            continue

        relevance, matched = calculate_relevance(article, topics)
        article['keywords_matched'] = matched
        article['category'] = detect_category(article, topics)

        engagement_score = min(article.get('engagement', 0) / 1000, 1.0)
        reputation_score = article['score'] / 100
        hours_old = (datetime.now() - pub_date).total_seconds() / 3600
        recency_score = max(0, 1 - hours_old / filters['max_age_hours'])

        final_score = (
            engagement_score * 0.3 +
            reputation_score * 0.25 +
            recency_score * 0.2 +
            relevance * 0.25
        ) * 100

        if final_score >= filters['min_total_score']:
            article['score'] = round(final_score)
            curated.append(article)

    curated.sort(key=lambda x: x['score'], reverse=True)
    return curated[:filters['max_items']]


def run_fetcher() -> dict:
    """Main fetcher function - returns curated articles"""
    all_articles = []

    # Fetch RSS feeds
    for feed in CONFIG['sources']['rss_feeds']:
        content = fetch_url(feed['url'])
        if content:
            articles = parse_rss_feed(content, feed['name'], feed['category'], feed['reputation'])
            all_articles.extend(articles)
        time.sleep(0.3)

    # Fetch Hacker News
    all_articles.extend(fetch_hackernews())

    # Fetch Reddit
    all_articles.extend(fetch_reddit())

    # Deduplicate
    seen = set()
    unique = []
    for a in all_articles:
        if a['url'] not in seen:
            seen.add(a['url'])
            unique.append(a)

    # Curate
    curated = curate_articles(unique)

    return {
        "lastUpdated": datetime.now().isoformat(),
        "count": len(curated),
        "articles": curated
    }


# ============ NEWSLETTER LOGIC ============

def generate_newsletter_html(articles: list[dict]) -> str:
    """Generate HTML email content"""
    top_articles = articles[:10]

    by_category = {}
    for a in top_articles:
        cat = a.get('category', 'news')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(a)

    category_info = {
        'news': {'emoji': '📰', 'title': 'AI News'},
        'tools': {'emoji': '🛠️', 'title': 'Tools & APIs'},
        'research': {'emoji': '🔬', 'title': 'Research'},
        'examples': {'emoji': '💡', 'title': 'Use Cases'},
        'business': {'emoji': '📈', 'title': 'Business'},
    }

    sections_html = ""
    for category, items in by_category.items():
        info = category_info.get(category, {'emoji': '📌', 'title': category.title()})
        items_html = ""
        for item in items:
            items_html += f'''
            <tr><td style="padding:16px 0;border-bottom:1px solid #eee;">
                <a href="{item['url']}" style="color:#1a1a2e;font-size:16px;font-weight:600;text-decoration:none;">{item['title']}</a>
                <p style="color:#666;font-size:14px;margin:8px 0 0;">{item['summary'][:150]}...</p>
                <p style="color:#999;font-size:12px;margin:4px 0 0;">{item['source']}</p>
            </td></tr>'''

        sections_html += f'''
        <tr><td style="padding:24px 0 12px;">
            <h2 style="color:#1a1a2e;font-size:18px;margin:0;">{info['emoji']} {info['title']}</h2>
        </td></tr>{items_html}'''

    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#f5f5f7;font-family:-apple-system,sans-serif;">
    <table width="100%" style="background:#f5f5f7;"><tr><td align="center" style="padding:40px 20px;">
    <table width="600" style="max-width:600px;">
        <tr><td style="background:linear-gradient(135deg,#1a1a2e,#0a0a0f);padding:32px;border-radius:16px 16px 0 0;">
            <h1 style="color:#fff;font-size:24px;margin:0;">⚡ AI Venture Digest</h1>
            <p style="color:#a0a0b0;font-size:14px;margin:4px 0 0;">{datetime.now().strftime('%B %d, %Y')}</p>
        </td></tr>
        <tr><td style="background:#fff;padding:24px 32px;">
            <table width="100%">{sections_html}</table>
        </td></tr>
        <tr><td style="background:#1a1a2e;padding:24px;border-radius:0 0 16px 16px;text-align:center;">
            <p style="color:#666;font-size:11px;margin:0;">
                <a href="*|UNSUB|*" style="color:#4a9eff;">Unsubscribe</a>
            </p>
        </td></tr>
    </table>
    </td></tr></table></body></html>'''


def send_mailchimp_campaign(articles: list[dict]) -> dict:
    """Send newsletter via Mailchimp API"""
    api_key = os.environ.get('MAILCHIMP_API_KEY')
    list_id = os.environ.get('MAILCHIMP_LIST_ID')

    if not api_key or not list_id:
        return {"status": "skipped", "reason": "Missing Mailchimp credentials"}

    dc = api_key.split('-')[-1] if '-' in api_key else 'us1'
    base_url = f"https://{dc}.api.mailchimp.com/3.0"
    auth = base64.b64encode(f"anystring:{api_key}".encode()).decode()

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth}'
    }

    # Create campaign
    campaign_data = json.dumps({
        "type": "regular",
        "recipients": {"list_id": list_id},
        "settings": {
            "subject_line": f"⚡ AI Digest: {articles[0]['title'][:40]}...",
            "title": f"AI Digest - {datetime.now().strftime('%Y-%m-%d')}",
            "from_name": "AI Venture Digest",
            "reply_to": os.environ.get('MAILCHIMP_REPLY_TO', 'digest@example.com')
        }
    }).encode()

    try:
        req = urllib.request.Request(f"{base_url}/campaigns", data=campaign_data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as resp:
            campaign = json.loads(resp.read().decode())

        campaign_id = campaign['id']

        # Set content
        html_content = generate_newsletter_html(articles)
        content_data = json.dumps({"html": html_content}).encode()
        req = urllib.request.Request(f"{base_url}/campaigns/{campaign_id}/content", data=content_data, headers=headers, method='PUT')
        urllib.request.urlopen(req)

        # Send
        req = urllib.request.Request(f"{base_url}/campaigns/{campaign_id}/actions/send", headers=headers, method='POST')
        urllib.request.urlopen(req)

        return {"status": "sent", "campaign_id": campaign_id}

    except urllib.error.HTTPError as e:
        return {"status": "error", "message": str(e), "body": e.read().decode()}


# ============ VERCEL HANDLER ============

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Verify cron secret (optional security)
        auth_header = self.headers.get('Authorization')
        cron_secret = os.environ.get('CRON_SECRET')

        if cron_secret and auth_header != f'Bearer {cron_secret}':
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
            return

        try:
            # Run the fetcher
            print("Starting fetch job...")
            result = run_fetcher()
            print(f"Fetched {result['count']} articles")

            # Send newsletter if we have articles
            newsletter_result = {"status": "skipped", "reason": "No articles"}
            if result['articles']:
                newsletter_result = send_mailchimp_campaign(result['articles'])
                print(f"Newsletter: {newsletter_result['status']}")

            response = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "articles_count": result['count'],
                "newsletter": newsletter_result
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
