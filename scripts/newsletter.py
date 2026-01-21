#!/usr/bin/env python3
import json
import os
import urllib.request
from datetime import datetime

def load_articles():
    with open('data/articles.json', 'r') as f:
        return json.load(f)

def generate_html(articles):
    top5 = articles[:5]
    html = f"""
    <h1>AI Venture Digest - {datetime.now().strftime('%B %d, %Y')}</h1>
    <h2>Top 5 Must-Reads</h2>
    <ol>
    """
    for a in top5:
        html += f'<li><a href="{a["url"]}">{a["title"]}</a><br><small>{a["source"]} | {a.get("category", "news")}</small><p>{a.get("summary", "")[:200]}...</p></li>'
    html += "</ol>"
    return html

def send_mailchimp(html_content):
    api_key = os.environ.get('MAILCHIMP_API_KEY')
    list_id = os.environ.get('MAILCHIMP_LIST_ID')
    reply_to = os.environ.get('MAILCHIMP_REPLY_TO', 'newsletter@example.com')
    if not api_key or not list_id:
        print("Missing Mailchimp credentials")
        return
    dc = api_key.split('-')[-1]
    campaign_data = json.dumps({
        "type": "regular",
        "recipients": {"list_id": list_id},
        "settings": {
            "subject_line": f"AI Venture Digest - {datetime.now().strftime('%B %d')}",
            "from_name": "AI Venture Digest",
            "reply_to": reply_to
        }
    }).encode()
    req = urllib.request.Request(
        f"https://{dc}.api.mailchimp.com/3.0/campaigns",
        data=campaign_data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            campaign = json.loads(resp.read())
            cid = campaign['id']
            content_data = json.dumps({"html": html_content}).encode()
            content_req = urllib.request.Request(
                f"https://{dc}.api.mailchimp.com/3.0/campaigns/{cid}/content",
                data=content_data,
                method='PUT',
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            )
            urllib.request.urlopen(content_req)
            if os.environ.get('NEWSLETTER_SEND_NOW') == 'true':
                send_req = urllib.request.Request(
                    f"https://{dc}.api.mailchimp.com/3.0/campaigns/{cid}/actions/send",
                    method='POST',
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                urllib.request.urlopen(send_req)
                print(f"Newsletter sent! Campaign: {cid}")
            else:
                print(f"Campaign created: {cid}")
    except Exception as e:
        print(f"Mailchimp error: {e}")

def main():
    data = load_articles()
    html = generate_html(data['articles'])
    send_mailchimp(html)

if __name__ == '__main__':
    main()
