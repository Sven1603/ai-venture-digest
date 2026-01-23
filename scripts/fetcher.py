#!/usr/bin/env python3
"""AI Venture Digest - Actionable Content Fetcher"""
import json, urllib.request, xml.etree.ElementTree as ET, re, html, os
from datetime import datetime

def load_config():
        with open('config.json', 'r') as f: return json.load(f)

    def is_actionable(title, desc=''):
            t = (title + ' ' + desc).lower()
            good = ['how to', 'tutorial', 'build', 'create', 'step by step', 'guide', 'from scratch', 'walkthrough', 'setup', 'automate', 'workflow', "let's build", 'code along', 'mvp', 'ship']
            bad = ['anaconda', 'jungle', 'wildlife', 'snake', 'paper analysis', 'arxiv', 'raises $', 'funding round', 'valuation', 'ipo', 'acquires', 'layoffs', 'weekly roundup']
            return not any(b in t for b in bad) and any(g in t for g in good)

def is_tool(title, desc=''):
        t = (title + ' ' + desc).lower()
        tools = ['cursor', 'claude', 'chatgpt', 'copilot', 'v0', 'bolt', 'replit', 'windsurf', 'langchain', 'n8n', 'zapier', 'vercel']
        return any(x in t for x in tools) and not any(x in t for x in ['raises', 'funding'])

def is_podcast_ok(title, desc=''):
        t = (title + ' ' + desc).lower()
        return any(x in t for x in ['ai', 'llm', 'claude', 'agent', 'startup', 'founder', 'saas', 'developer', 'rag', 'prompt'])

def get_thumb(entry):
        for c in entry:
                    if 'thumbnail' in c.tag.lower(): return c.get('url') or c.text
                            return None

def fetch_rss(url, name, rep, ctype='article'):
        arts = []
        try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as r: content = r.read().decode('utf-8', errors='ignore')
                                root = ET.fromstring(content)
                    for item in (root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry'))[:15]:
                                    title = item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title') or ''
                                    link = item.findtext('link') or ''
                                    if not link:
                                                        le = item.find('{http://www.w3.org/2005/Atom}link')
                                                        if le is not None: link = le.get('href', '')
                                                                        desc = re.sub(r'<[^>]+>', '', item.findtext('description') or item.findtext('{http://www.w3.org/2005/Atom}summary') or '')[:300]
                                                    desc = html.unescape(desc)
                                    pub = item.findtext('pubDate') or item.findtext('{http://www.w3.org/2005/Atom}published') or ''
                                    thumb = get_thumb(item)
                                    vid = None
                                    if 'youtube.com' in link or 'youtu.be' in link:
                                                        vid = link
                                                        m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', link)
                                                        if m and not thumb: thumb = f"https://img.youtube.com/vi/{m.group(1)}/hqdefault.jpg"
                                                                        if title and link:
                                                                                            arts.append({'title': html.unescape(title.strip()), 'url': link.strip(), 'description': desc.strip(), 'source': name, 'reputation': rep, 'published': pub, 'thumbnail': thumb, 'video_url': vid, 'content_type': ctype, 'fetched_at': datetime.now().isoformat()})
        except Exception as e: print(f"  Warn {name}: {e}")
                return arts

def fetch_youtube(cfg):
        print("\nYouTube tutorials...")
    vids = []
    for ch in cfg['sources'].get('youtube_channels', []):
                url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['channel_id']}"
                for v in fetch_rss(url, ch['name'], ch['reputation'], 'video'):
                                if is_actionable(v['title'], v.get('description', '')):
                                                    v['category'] = 'tutorial'
                                                    vids.append(v)
elif is_tool(v['title'], v.get('description', '')):
                v['category'] = 'tools'
                vids.append(v)
    print(f"  Found {len(vids)} videos")
    return vids

def fetch_podcasts(cfg):
        print("\nPodcasts...")
    eps = []
    for p in cfg['sources'].get('podcasts', []):
                for e in fetch_rss(p['url'], p['name'], p['reputation'], 'podcast')[:5]:
                                if is_podcast_ok(e['title'], e.get('description', '')):
                                                    e['category'] = 'podcast'
                                                    e['is_podcast'] = True
                                                    eps.append(e)
                                        print(f"  Found {len(eps)} episodes")
                        return eps

def fetch_blogs(cfg):
        print("\nBlogs...")
    arts = []
    for f in cfg['sources'].get('rss_feeds', []):
                for a in fetch_rss(f['url'], f['name'], f['reputation']):
                                if is_actionable(a['title'], a.get('description', '')):
                                                    a['category'] = 'deep_dive'
                                                    arts.append(a)
elif is_tool(a['title'], a.get('description', '')):
                a['category'] = 'tools'
                arts.append(a)
    print(f"  Found {len(arts)} posts")
    return arts

def get_skills(cfg):
        print("\nSkills...")
    return [{'title': s['name'], 'url': s['url'], 'description': s['description'], 'source': 'GitHub', 'reputation': 0.95, 'category': 'skill', 'fetched_at': datetime.now().isoformat()} for s in cfg['sources'].get('github_skills', [])]

def fetch_twitter(cfg):
        print("\nX/Twitter...")
    posts = []
    accts = cfg['sources'].get('twitter_accounts', [])
    instances = cfg['sources'].get('nitter_instances', ['https://nitter.poast.org'])
    for a in accts:
                for inst in instances:
                                try:
                                                    req = urllib.request.Request(f"{inst}/{a['handle']}/rss", headers={'User-Agent': 'Mozilla/5.0'})
                                                    with urllib.request.urlopen(req, timeout=10) as r: content = r.read().decode('utf-8', errors='ignore')
                                                                        for item in ET.fromstring(content).findall('.//item')[:3]:
                                                                                                title = item.findtext('title') or ''
                                                                                                link = item.findtext('link') or ''
                                                                                                if title.startswith('RT by'): continue
                                                                                                                        t = title.lower()
                                                                                                if any(k in t for k in ['ai', 'llm', 'claude', 'cursor', 'agent', 'build', 'ship', 'tool']):
                                                                                                                            posts.append({'title': title[:200], 'url': link.replace(inst, 'https://x.com'), 'source': f"@{a['handle']}", 'author': a['name'], 'category': 'twitter', 'fetched_at': datetime.now().isoformat()})
                                                                                                                    break
                                                                                        except: continue
                                                                                                print(f"  Found {len(posts)} posts")
    return posts

def score(art, cfg):
        s = art.get('reputation', 0.5) * 0.25
    t = (art.get('title', '') + ' ' + art.get('description', '')).lower()
    s += min(sum(1 for x in cfg.get('topics', []) if x in t) / 3, 1.0) * 0.3
    s += {'tutorial': 0.25, 'deep_dive': 0.2, 'skill': 0.2, 'tools': 0.15, 'podcast': 0.12}.get(art.get('category', ''), 0)
    return s

def quick_wins(arts, skills):
        qw = []
    tools = [a for a in arts if a.get('category') == 'tools']
    if tools: qw.append({'type': 'new_tool', 'label': 'New Tool', **max(tools, key=lambda x: x.get('score', 0))})
            if skills: qw.append({'type': 'skill', 'label': 'Claude Skill', **skills[0]})
                    tuts = [a for a in arts if a.get('category') == 'tutorial']
    if tuts: qw.append({'type': 'tutorial', 'label': 'Quick Tutorial', **max(tuts, key=lambda x: x.get('score', 0))})
            return qw

def main():
        print("=" * 50 + "\nAI Venture Digest Fetcher v2.1\n" + "=" * 50)
    cfg = load_config()
    arts = fetch_youtube(cfg) + fetch_podcasts(cfg) + fetch_blogs(cfg) + get_skills(cfg) + fetch_twitter(cfg)
    for a in arts: a['score'] = score(a, cfg)
            arts.sort(key=lambda x: x['score'], reverse=True)
    skills = [a for a in arts if a.get('category') == 'skill']
    pods = [a for a in arts if a.get('category') == 'podcast']
    twit = [a for a in arts if a.get('category') == 'twitter'][:5]
    qw = quick_wins(arts, skills)
    fp = pods[0] if pods else None
    cats = {}
    for a in arts: cats[a.get('category', 'other')] = cats.get(a.get('category', 'other'), 0) + 1
            arts = arts[:cfg['filters'].get('max_articles', 30)]
    os.makedirs('data', exist_ok=True)
    with open('data/articles.json', 'w') as f:
                json.dump({'generated_at': datetime.now().isoformat(), 'article_count': len(arts), 'quick_wins': qw, 'featured_podcast': fp, 'twitter_posts': twit, 'categories': cats, 'articles': arts}, f, indent=2)
    print(f"\nSaved {len(arts)} articles. Done!")

if __name__ == '__main__': main()
