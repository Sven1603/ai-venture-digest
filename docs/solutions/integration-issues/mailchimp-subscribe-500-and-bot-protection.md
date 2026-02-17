---
title: "Mailchimp Subscribe 500 Error and Bot Protection"
category: integration-issues
module: api/subscribe.py
tags:
  - mailchimp
  - vercel
  - environment-variables
  - bot-protection
  - subscribe
severity: high
date_resolved: 2026-02-17
symptoms:
  - "Subscribe returns 500: {\"error\": \"config\", \"message\": \"Something went wrong.\"}"
  - "Mailchimp double opt-in confirmation page redirects to 404"
  - "Legitimate users silently rejected by time-based bot check"
---

# Mailchimp Subscribe 500 Error and Bot Protection

## Problem

The subscribe endpoint (`/api/subscribe`) returned a 500 error with `{"error": "config"}` when users tried to subscribe via the website.

## Symptoms

- Subscribe button shows "Something went wrong. Please try again later."
- Error response body: `{"error": "config", "message": "Something went wrong. Please try again later."}`
- Subscriptions work from GitHub Actions (newsletter) but not from the Vercel-hosted site

## Root Cause

`MAILCHIMP_API_KEY` and `MAILCHIMP_LIST_ID` were configured in **GitHub Actions secrets** but not in **Vercel environment variables**. The serverless function at `api/subscribe.py` checks for these on lines 29-31 and returns the "config" error when they're missing.

GitHub Actions and Vercel have completely separate secret/env var stores. Setting a secret in one does not make it available in the other.

## Solution

### 1. Add env vars to Vercel

Vercel dashboard > Project Settings > Environment Variables:
- `MAILCHIMP_API_KEY` (format: `xxxxxxxx-usXX`)
- `MAILCHIMP_LIST_ID`

Redeploy after adding (env vars only take effect on new deployments).

### 2. Retrieving secrets from GitHub Actions

GitHub secrets are write-only — you can't read them back from the UI or API. Workaround: create a temporary workflow that base64-encodes the secrets (bypasses GitHub's log masking):

```yaml
# .github/workflows/reveal-secrets.yml (temporary — delete after use)
name: Reveal Secrets
on: workflow_dispatch
jobs:
  reveal:
    runs-on: ubuntu-latest
    steps:
      - name: Show secrets
        env:
          MC_KEY: ${{ secrets.MAILCHIMP_API_KEY }}
          MC_LIST: ${{ secrets.MAILCHIMP_LIST_ID }}
        run: |
          echo "$MC_KEY" | base64
          echo "$MC_LIST" | base64
```

Decode with: `echo "<base64-output>" | base64 --decode`

**Delete the workflow immediately after use.**

## Additional Issues Found

### Double opt-in redirect 404

Mailchimp's confirmation "thank you" page redirected to a 404. Custom redirect URLs require a paid Mailchimp plan.

**Fix:** Changed `status: "pending"` to `status: "subscribed"` in the Mailchimp API call. Users are subscribed directly without a confirmation page.

**Trade-off:** No email ownership verification. Mitigated by bot protection (below).

### Bot protection (replacing double opt-in verification)

Added two layers of bot protection:

1. **Honeypot field** (pre-existing): Hidden `website` input that bots auto-fill. Server silently rejects if filled.
2. **Time-based check** (new): Client sends `t_open` (modal opened) and `t_submit` (form submitted). Server rejects if delta < 3 seconds. Bots submit instantly; humans don't.

Both traps return a fake `200 {"success": true}` to avoid revealing detection to bots.

### Clock skew bug (found during code review)

The initial time check compared `Date.now()` (client) with `time.time()` (server) — two different clocks. Users with device clocks even a few seconds off were **silently rejected** with a fake success response.

**Fix:** Send both timestamps from the client (`t_open`, `t_submit`) so the delta uses the same clock:

```javascript
// index.html
body: JSON.stringify({ email, website: honeypot, t_open: subscribeOpenedAt, t_submit: Date.now() })
```

```python
# api/subscribe.py
opened_at = body.get('t_open', 0)
submitted_at = body.get('t_submit', 0)
if not opened_at or not submitted_at or (submitted_at - opened_at) < 3000:
    self._respond(200, {"success": True, "message": "You've been subscribed!"})
    return
```

## Prevention

- **Environment variables for serverless functions must be set in Vercel separately from GitHub Actions.** They are independent stores.
- **Never compare client and server clocks.** If you need a time delta, ensure both timestamps come from the same source.
- **Test subscribe endpoints in production immediately after deploy.** Local testing won't catch missing env vars in serverless environments.

## Related Documentation

- [Vercel Analytics Ad Blocker Proxy](./vercel-analytics-blocked-by-adblockers.md) — another Vercel integration issue
- [Uncommitted Config After Rewrite](../runtime-errors/uncommitted-config-after-rewrite.md) — Mailchimp 204 response handling
- [Analytics and Subscribe Plan](../../plans/2026-02-17-feat-analytics-and-working-subscribe-plan.md) — original implementation plan

## Files Changed

- `api/subscribe.py` — Bot protection, direct subscribe, clock skew fix
- `index.html` — Timestamp tracking for subscribe modal
