#!/usr/bin/env python3
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
import os

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def fetch_rss(url, source_name, reputation):
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AIVentureDigest/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            root = ET.parse(response).getroot()
            for item in root.findall('.//item')[:10]:
                title = item.find('title')
                link = item.find('link')
                desc = item.find('description')
                pub_date = item.find('pubDate')
                if title is not None and link is not None:
                    articles.append({
                        'title': title.text or '',
                        'url': link.text or '',
                        'source': source_name,
                        'summary': (desc.text or '')[:300] if desc is not None else '',
                        'published': pub_date.text if pub_date is not None else datetime.now().isoformat(),
                        'reputation': reputation
                    })
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
    return articles

def calculate_score(article, config):
    weights = config['filters']
    score = 0
    score += article.get('reputation', 0.5) * 100 * weights['reputation_weight']
    topics = config.get('topics', [])
    text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
    relevance = sum(1 for t in topics if t.lower() in text) / max(len(topics), 1)
    score += relevance * 100 * weights['relevance_weight']
    score += 50 * weights['recency_weight']
    score += 50 * weights['engagement_weight']
    return round(score, 1)

def categorize(article):
    title = article.get('title', '').lower()
    if any(w in title for w in ['tutorial', 'guide', 'how to', 'build']):
        return 'examples'
    if any(w in title for w in ['tool', 'release', 'launch', 'update']):
        return 'tools'
    if any(w in title for w in ['funding', 'startup', 'business', 'invest']):
        return 'business'
    if any(w in title for w in ['research', 'paper', 'study']):
        return 'research'
    return 'news'

def main():
    config = load_config()
    all_articles = []
    for feed in config['sources']['rss_feeds']:
        articles = fetch_rss(feed['url'], feed['name'], feed['reputation'])
        all_articles.extend(articles)
    for article in all_articles:
        article['score'] = calculate_score(article, config)
        article['category'] = categorize(article)
    all_articles.sort(key=lambda x: x['score'], reverse=True)
    all_articles = all_articles[:config['filters']['max_articles']]
    output = {
        'last_updated': datetime.now().isoformat() + 'Z',
        'articles': all_articles
    }
    os.makedirs('data', exist_ok=True)
    with open('data/articles.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Fetched {len(all_articles)} articles")

if __name__ == '__main__':
    main()
