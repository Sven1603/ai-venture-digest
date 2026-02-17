---
title: "feat: Add Vercel Analytics and working Mailchimp subscribe"
type: feat
date: 2026-02-17
brainstorm: docs/brainstorms/2026-02-17-analytics-and-subscribe-brainstorm.md
---

# feat: Add Vercel Analytics and working Mailchimp subscribe

## Overview

Close two operational gaps in the site: the subscribe button currently shows an `alert()` stub and there's zero analytics. This plan connects the subscribe modal to Mailchimp via a Vercel serverless endpoint and adds Vercel Web Analytics for page view tracking.

No new Python dependencies. Reuses existing Mailchimp credentials and Vercel serverless patterns.

## Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------|
| `api/subscribe.py` | **Create** | Vercel serverless POST endpoint — validates email, calls Mailchimp API |
| `index.html` | **Modify** | Wire up subscribe form, add honeypot field, add analytics script |
| `vercel.json` | No change | Auto-detects `api/subscribe.py` — no config needed (per CLAUDE.md) |

## 1. Create `api/subscribe.py`

Vercel serverless function following the exact pattern from `api/cron/fetch.py`.

### Handler structure

```python
import json
import os
import base64
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode())

            email = body.get('email', '').strip().lower()
            honeypot = body.get('website', '')  # honeypot field

            # Honeypot check — bots fill this, humans don't
            if honeypot:
                self._respond(200, {"success": True, "message": "Check your inbox to confirm."})
                return

            # Validate email
            if not email or '@' not in email or '.' not in email.split('@')[-1]:
                self._respond(400, {"error": "invalid_email", "message": "Please enter a valid email address."})
                return

            # Check Mailchimp credentials
            api_key = os.environ.get('MAILCHIMP_API_KEY')
            list_id = os.environ.get('MAILCHIMP_LIST_ID')
            if not api_key or not list_id:
                self._respond(500, {"error": "config", "message": "Something went wrong. Please try again later."})
                return

            # Call Mailchimp API
            dc = api_key.split('-')[-1] if '-' in api_key else 'us1'
            url = f"https://{dc}.api.mailchimp.com/3.0/lists/{list_id}/members"
            auth = base64.b64encode(f"anystring:{api_key}".encode()).decode()

            data = json.dumps({
                "email_address": email,
                "status": "pending"  # double opt-in
            }).encode()

            req = urllib.request.Request(url, data=data, headers={
                'Content-Type': 'application/json',
                'Authorization': f'Basic {auth}'
            }, method='POST')

            with urllib.request.urlopen(req) as response:
                resp_body = response.read().decode()
                # Mailchimp may return empty body — handle before json.loads
                result = json.loads(resp_body) if resp_body else {}

            self._respond(200, {"success": True, "message": "Check your inbox to confirm your subscription."})

        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            try:
                error_data = json.loads(error_body) if error_body else {}
            except json.JSONDecodeError:
                error_data = {}

            if e.code == 400 and error_data.get('title') == 'Member Exists':
                self._respond(200, {"success": True, "message": "You're already on the list! Check your inbox."})
            else:
                self._respond(500, {"error": "api", "message": "Something went wrong. Please try again later."})

        except Exception:
            self._respond(500, {"error": "server", "message": "Something went wrong. Please try again later."})

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # suppress default stderr logging
```

### Key decisions

- **`status: "pending"`** — triggers Mailchimp's double opt-in confirmation email automatically
- **"Member Exists" returns 200 with a friendly message** — not an error from the user's perspective
- **Honeypot field named `website`** — plausible label that bots auto-fill. If filled, return fake success (200) so bots think it worked
- **Server-side honeypot check** — protects against direct API calls, not just browser submissions
- **Empty body handling** — `json.loads(resp_body) if resp_body else {}` per documented gotcha
- **`log_message` suppressed** — avoids noisy stderr in Vercel function logs

### Response contract

| Scenario | HTTP Status | Body |
|----------|-------------|------|
| Success (pending) | 200 | `{"success": true, "message": "Check your inbox to confirm your subscription."}` |
| Already subscribed | 200 | `{"success": true, "message": "You're already on the list! Check your inbox."}` |
| Bot detected | 200 | `{"success": true, "message": "Check your inbox to confirm."}` (fake success) |
| Invalid email | 400 | `{"error": "invalid_email", "message": "Please enter a valid email address."}` |
| Mailchimp error | 500 | `{"error": "api", "message": "Something went wrong. Please try again later."}` |
| Missing env vars | 500 | `{"error": "config", "message": "Something went wrong. Please try again later."}` |

## 2. Update `index.html` — Subscribe Modal

### 2a. Add honeypot field to modal HTML (~line 753)

Add a hidden `website` input after the email input:

```html
<input type="email" id="subscribeEmail" placeholder="your@email.com">
<input type="text" id="subscribeWebsite" name="website" autocomplete="off"
       tabindex="-1" style="position:absolute;left:-9999px;opacity:0;">
```

- `tabindex="-1"` prevents keyboard users from landing on it
- `position:absolute;left:-9999px` hides from visual users
- `autocomplete="off"` prevents browser autofill
- No `aria-hidden` needed since it's off-screen

### 2b. Replace `subscribe()` function (~lines 1168-1176)

Replace the stub with a real fetch call:

```javascript
async function subscribe() {
    const email = document.getElementById('subscribeEmail').value;
    const honeypot = document.getElementById('subscribeWebsite').value;
    const btn = document.querySelector('#subscribeModal .btn-primary');

    if (!email || !email.includes('@')) {
        showSubscribeMessage('Please enter a valid email address.', true);
        return;
    }

    // Loading state
    btn.disabled = true;
    btn.textContent = 'Subscribing...';

    try {
        const response = await fetch('/api/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, website: honeypot })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showSubscribeMessage(data.message, false);
            setTimeout(() => {
                closeSubscribeModal();
                resetSubscribeModal();
            }, 3000);
        } else {
            showSubscribeMessage(data.message || 'Something went wrong.', true);
        }
    } catch (e) {
        showSubscribeMessage('Network error. Please try again.', true);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Subscribe';
    }
}

function showSubscribeMessage(msg, isError) {
    let el = document.getElementById('subscribeMessage');
    if (!el) {
        el = document.createElement('p');
        el.id = 'subscribeMessage';
        const input = document.getElementById('subscribeEmail');
        input.parentNode.insertBefore(el, input.nextSibling);
    }
    el.textContent = msg;
    el.style.color = isError ? '#ef4444' : '#10b981';
    el.style.fontSize = '14px';
    el.style.marginTop = '8px';
}

function resetSubscribeModal() {
    document.getElementById('subscribeEmail').value = '';
    document.getElementById('subscribeWebsite').value = '';
    const msg = document.getElementById('subscribeMessage');
    if (msg) msg.remove();
}
```

### 2c. Update `closeSubscribeModal()` (~line 1164)

Clear error/success messages when modal closes (keep email value as convenience):

```javascript
function closeSubscribeModal() {
    document.getElementById('subscribeModal').classList.remove('active');
    const msg = document.getElementById('subscribeMessage');
    if (msg) msg.remove();
}
```

### 2d. Add Escape key handler

Add near the existing backdrop-click handler (~line 1178):

```javascript
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSubscribeModal();
});
```

## 3. Add Vercel Web Analytics to `index.html`

### 3a. Enable in Vercel Dashboard (manual step)

Go to Vercel Dashboard → select the project → **Analytics** tab → click **Enable**.

This creates the `/_vercel/insights/*` routes on the next deployment.

### 3b. Add script tag before `</body>` (~line 1183)

```html
    <script>
        window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
    </script>
    <script defer src="/_vercel/insights/script.js"></script>
</body>
```

That's it — Vercel handles everything else. View data at Dashboard → Analytics tab.

## Acceptance Criteria

- [x] Entering a valid email and clicking Subscribe calls `/api/subscribe` and shows "Check your inbox to confirm your subscription."
- [x] Mailchimp receives the subscriber with `status: pending` and sends the double opt-in email
- [x] Submitting an already-subscribed email shows "You're already on the list!"
- [x] Invalid email shows client-side validation error without hitting the API
- [x] Button shows "Subscribing..." and is disabled during the request
- [x] Modal auto-closes 3 seconds after successful submission
- [x] Honeypot field is invisible to users but catches bots (silent fake-success)
- [x] Escape key closes the modal
- [x] Vercel Analytics script loads and tracks page views (verify via Network tab: `/_vercel/insights/view`)
- [x] No new Python dependencies added

## What's NOT included

- Subscriber count displayed on site (use Mailchimp dashboard)
- Rate limiting (rely on Mailchimp's abuse detection)
- reCAPTCHA or heavy bot protection
- Custom analytics events beyond page views
- Speed Insights (only Web Analytics)
