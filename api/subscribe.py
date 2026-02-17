import json
import os
import base64
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode())

            email = body.get('email', '').strip().lower()
            honeypot = body.get('website', '')

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
                "status": "pending"
            }).encode()

            req = urllib.request.Request(url, data=data, headers={
                'Content-Type': 'application/json',
                'Authorization': f'Basic {auth}'
            }, method='POST')

            with urllib.request.urlopen(req) as response:
                resp_body = response.read().decode()
                json.loads(resp_body) if resp_body else {}

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
        pass
