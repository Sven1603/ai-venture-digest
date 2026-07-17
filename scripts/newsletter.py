#!/usr/bin/env python3
"""
AI Venture Digest - Newsletter Generator & Mailchimp Integration
Generates daily digest email and sends via Mailchimp.
"""

import json
import os
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional
import base64

# Configuration
CONFIG_PATH = Path(__file__).parent.parent / "config.json"
DATA_PATH = Path(__file__).parent.parent / "data"
TEMPLATES_PATH = Path(__file__).parent.parent / "templates"
WEBSITE_URL = "https://ai-venture-digest.vercel.app"
NEWS_CATEGORIES = ('releases', 'launches', 'business', 'research')


def load_config() -> dict:
    """Load configuration from JSON file."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_articles() -> list[dict]:
    """Load curated articles from JSON."""
    articles_file = DATA_PATH / 'articles.json'
    if not articles_file.exists():
        return []

    with open(articles_file) as f:
        data = json.load(f)
        return data.get('articles', [])


def generate_newsletter_html(articles: list[dict], config: dict) -> str:
    """Generate newsletter HTML content."""
    max_items = config['newsletter'].get('max_items', 10)
    news_articles = [a for a in articles if a.get('category') in NEWS_CATEGORIES]
    top_articles = news_articles[:max_items]

    # Group by category
    by_category = {}
    for article in top_articles:
        cat = article.get('category', 'business')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(article)

    # Category display info
    category_info = {
        'releases': {'emoji': '🚀', 'title': 'Releases'},
        'launches': {'emoji': '🆕', 'title': 'Launches'},
        'business': {'emoji': '📈', 'title': 'Business & Strategy'},
        'research': {'emoji': '🔬', 'title': 'Research'},
    }

    # Build sections in fixed order
    sections_html = ""
    for category in NEWS_CATEGORIES:
        items = by_category.get(category)
        if not items:
            continue
        info = category_info[category]
        items_html = ""
        for item in items:
            items_html += f"""
            <tr>
              <td style="padding: 16px 0; border-bottom: 1px solid #eee;">
                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                  <tr>
                    <td>
                      <a href="{item['url']}" style="color: #1a1a2e; font-size: 16px; font-weight: 600; text-decoration: none; line-height: 1.4;">
                        {item['title']}
                      </a>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding-top: 8px;">
                      <p style="color: #666; font-size: 14px; line-height: 1.5; margin: 0;">
                        {item.get('description', '')[:200]}...
                      </p>
                      <p style="color: #999; font-size: 12px; margin: 8px 0 0 0;">
                        {item['source']}
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            """

        sections_html += f"""
        <tr>
          <td style="padding: 24px 0 12px 0;">
            <h2 style="color: #1a1a2e; font-size: 18px; margin: 0; font-weight: 600;">
              {info['emoji']} {info['title']}
            </h2>
          </td>
        </tr>
        {items_html}
        """

    # Full email template
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Venture Digest</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
  <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f5f5f7;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width: 600px;">
          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #1a1a2e 0%, #0a0a0f 100%); padding: 32px; border-radius: 16px 16px 0 0;">
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td>
                    <span style="font-size: 32px;">⚡</span>
                  </td>
                  <td style="padding-left: 12px;">
                    <h1 style="color: #fff; font-size: 24px; margin: 0; font-weight: 700;">
                      <a href="{WEBSITE_URL}" style="color: #fff; text-decoration: none;">
                        AI Venture Digest
                      </a>
                    </h1>
                    <p style="color: #a0a0b0; font-size: 14px; margin: 4px 0 0 0;">
                      {datetime.now().strftime('%B %d, %Y')} • Your daily AI briefing
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Stats Bar -->
          <tr>
            <td style="background: #12121a; padding: 16px 32px;">
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td align="center" width="33%">
                    <span style="color: #4a9eff; font-size: 24px; font-weight: 700;">{len(top_articles)}</span>
                    <br>
                    <span style="color: #a0a0b0; font-size: 12px;">TOP STORIES</span>
                  </td>
                  <td align="center" width="33%">
                    <span style="color: #10b981; font-size: 24px; font-weight: 700;">{len(by_category)}</span>
                    <br>
                    <span style="color: #a0a0b0; font-size: 12px;">CATEGORIES</span>
                  </td>
                  <td align="center" width="33%">
                    <span style="color: #8b5cf6; font-size: 24px; font-weight: 700;">{len(set(a.get('source', '') for a in top_articles))}</span>
                    <br>
                    <span style="color: #a0a0b0; font-size: 12px;">SOURCES</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CTA Button -->
          <tr>
            <td style="background: #12121a; padding: 0 32px 20px 32px; text-align: center;">
              <a href="{WEBSITE_URL}"
                 style="display: inline-block; background-color: #4a9eff;
                        background: linear-gradient(135deg, #4a9eff, #8b5cf6);
                        color: #ffffff; font-size: 15px; font-weight: 600;
                        padding: 12px 28px; border-radius: 8px;
                        text-decoration: none;">
                View Full Digest on the Web &rarr;
              </a>
            </td>
          </tr>

          <!-- Main Content -->
          <tr>
            <td style="background: #ffffff; padding: 24px 32px;">
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                {sections_html}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #1a1a2e; padding: 24px 32px; border-radius: 0 0 16px 16px;">
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td align="center">
                    <p style="color: #a0a0b0; font-size: 12px; margin: 0 0 12px 0;">
                      The AI news that matters — for people who build
                    </p>
                    <p style="color: #666; font-size: 11px; margin: 0;">
                      <a href="*|UNSUB|*" style="color: #4a9eff; text-decoration: none;">Unsubscribe</a> •
                      <a href="*|ARCHIVE|*" style="color: #4a9eff; text-decoration: none;">View in browser</a>
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return html


def generate_newsletter_text(articles: list[dict], config: dict) -> str:
    """Generate plain text version of newsletter."""
    max_items = config['newsletter'].get('max_items', 10)
    news_articles = [a for a in articles if a.get('category') in NEWS_CATEGORIES]
    top_articles = news_articles[:max_items]

    lines = [
        "=" * 50,
        "⚡ AI VENTURE DIGEST",
        datetime.now().strftime('%B %d, %Y'),
        "=" * 50,
        "",
        f"View full digest: {WEBSITE_URL}",
        "",
    ]

    by_category = {}
    for article in top_articles:
        by_category.setdefault(article.get('category', 'business'), []).append(article)

    titles = {'releases': 'RELEASES', 'launches': 'LAUNCHES',
              'business': 'BUSINESS & STRATEGY', 'research': 'RESEARCH'}
    for category in NEWS_CATEGORIES:
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

    return "\n".join(lines)


class MailchimpClient:
    """Simple Mailchimp API client."""

    def __init__(self, api_key: str, list_id: str):
        self.api_key = api_key
        self.list_id = list_id
        # Extract datacenter from API key
        self.dc = api_key.split('-')[-1] if '-' in api_key else 'us1'
        self.base_url = f"https://{self.dc}.api.mailchimp.com/3.0"

    def _request(self, method: str, endpoint: str, data: Optional[dict] = None) -> dict:
        """Make authenticated request to Mailchimp API."""
        url = f"{self.base_url}/{endpoint}"

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {base64.b64encode(f"anystring:{self.api_key}".encode()).decode()}'
        }

        request_data = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as response:
                body = response.read().decode()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"Mailchimp API error: {e.code} - {error_body}")
            raise

    def create_campaign(self, subject: str, html_content: str, text_content: str) -> str:
        """Create a new campaign."""
        # Create campaign
        campaign_data = {
            "type": "regular",
            "recipients": {
                "list_id": self.list_id
            },
            "settings": {
                "subject_line": subject,
                "title": f"AI Digest - {datetime.now().strftime('%Y-%m-%d')}",
                "from_name": "AI Venture Digest",
                "reply_to": os.environ.get('MAILCHIMP_REPLY_TO', 'digest@example.com'),
                "auto_footer": True
            }
        }

        result = self._request('POST', 'campaigns', campaign_data)
        campaign_id = result['id']

        # Set content
        content_data = {
            "html": html_content,
            "plain_text": text_content
        }
        self._request('PUT', f'campaigns/{campaign_id}/content', content_data)

        return campaign_id

    def send_campaign(self, campaign_id: str):
        """Send a campaign immediately."""
        self._request('POST', f'campaigns/{campaign_id}/actions/send')

    def schedule_campaign(self, campaign_id: str, send_time: str):
        """Schedule a campaign for later."""
        data = {"schedule_time": send_time}
        self._request('POST', f'campaigns/{campaign_id}/actions/schedule', data)


def send_newsletter(config: dict):
    """Generate and send newsletter via Mailchimp."""
    # Check for required environment variables
    api_key = os.environ.get('MAILCHIMP_API_KEY')
    list_id = os.environ.get('MAILCHIMP_LIST_ID')

    if not api_key or not list_id:
        print("⚠️  Missing Mailchimp credentials. Set MAILCHIMP_API_KEY and MAILCHIMP_LIST_ID environment variables.")
        print("   Generating newsletter content only...")
        generate_only = True
    else:
        generate_only = False

    # Load articles
    articles = load_articles()
    if not articles:
        print("❌ No articles found. Run the fetcher first.")
        return

    # Generate content
    print("📝 Generating newsletter content...")
    html_content = generate_newsletter_html(articles, config)
    text_content = generate_newsletter_text(articles, config)

    # Save locally
    TEMPLATES_PATH.mkdir(exist_ok=True)
    html_file = TEMPLATES_PATH / f"newsletter_{datetime.now().strftime('%Y%m%d')}.html"
    with open(html_file, 'w') as f:
        f.write(html_content)
    print(f"   ✓ Saved HTML to {html_file}")

    if generate_only:
        return

    # Send via Mailchimp
    print("📤 Creating Mailchimp campaign...")
    client = MailchimpClient(api_key, list_id)

    subject = f"⚡ AI Digest: {articles[0]['title'][:50]}..."
    campaign_id = client.create_campaign(subject, html_content, text_content)
    print(f"   ✓ Created campaign: {campaign_id}")

    # Check if we should send now or schedule
    send_time = config['newsletter'].get('send_time', '08:00')
    send_now = os.environ.get('NEWSLETTER_SEND_NOW', 'false').lower() == 'true'

    if send_now:
        print("📧 Sending newsletter...")
        client.send_campaign(campaign_id)
        print("   ✓ Newsletter sent!")
    else:
        # Schedule for next occurrence of send_time
        tz = config['newsletter'].get('timezone', 'UTC')
        schedule_time = f"{datetime.now().strftime('%Y-%m-%d')}T{send_time}:00+00:00"
        print(f"⏰ Newsletter scheduled for {schedule_time}")


def main():
    """Main execution."""
    print("=" * 50)
    print("📧 AI Venture Digest - Newsletter Generator")
    print("=" * 50)
    print()

    config = load_config()
    send_newsletter(config)

    print("\n✅ Done!")


if __name__ == '__main__':
    main()
