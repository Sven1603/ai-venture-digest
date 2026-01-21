from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            articles = self.fetch_content()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'count': len(articles)}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def fetch_content(self):
        feeds = [
            ('TechCrunch AI', 'https://techcrunch.com/category/artificial-intelligence/feed/', 0.9),
            ('OpenAI Blog', 'https://openai.com/blog/rss.xml', 1.0),
            ('Anthropic Blog', 'https://www.anthropic.com/index/rss.xml', 1.0)
        ]
        articles = []
        for name, url, rep in feeds:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'AIVentureDigest/1.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    root = ET.parse(resp).getroot()
                    for item in root.findall('.//item')[:5]:
                        title = item.find('title')
                        link = item.find('link')
                        if title is not None and link is not None:
                            articles.append({
                                'title': title.text,
                                'url': link.text,
                                'source': name,
                                'score': rep * 100
                            })
            except:
                pass
        return articles
