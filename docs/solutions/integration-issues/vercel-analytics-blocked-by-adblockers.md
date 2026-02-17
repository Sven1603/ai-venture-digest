---
title: Vercel Analytics script blocked by ad blockers
category: integration-issues
module: index.html, vercel.json
tags: [vercel, analytics, ad-blocker, rewrites, proxy]
severity: medium
date: 2026-02-17
---

# Vercel Analytics script blocked by ad blockers

## Symptom

After adding Vercel Web Analytics to `index.html`, the script fails to load with:

```
GET https://ai-venture-digest.vercel.app/_vercel/insights/script.js net::ERR_BLOCKED_BY_CLIENT
```

No analytics data appears in the Vercel dashboard. Affects users running uBlock Origin, Brave, AdGuard, and similar ad/tracker blockers.

## Root Cause

Ad blocker filter lists pattern-match on `/_vercel/insights/` — a known analytics endpoint path. The browser blocks the request before it reaches the server. This is not a configuration error; the analytics setup is correct but the client refuses to load the script.

Google Analytics (`google-analytics.com`, `googletagmanager.com`) is blocked even more aggressively since it loads from a third-party domain. Vercel's first-party path is better but still recognized by updated filter lists.

## Solution

Proxy the analytics script through a custom path using Vercel rewrites. The browser only sees a request to your own domain at a generic-looking path.

### 1. Add rewrite to `vercel.json`

```json
{
  "rewrites": [
    {
      "source": "/data/lib/:match*",
      "destination": "https://ai-venture-digest.vercel.app/_vercel/insights/:match*"
    }
  ]
}
```

**Important:** The destination must be a full URL (including domain), not a relative path — relative paths don't work for Vercel rewrites to internal routes.

### 2. Update script tag in `index.html`

Before:
```html
<script defer src="/_vercel/insights/script.js"></script>
```

After:
```html
<script defer src="/data/lib/script.js" data-endpoint="/data/lib"></script>
```

The `data-endpoint` attribute tells the analytics script where to POST pageview data (also through the proxy path).

### 3. Keep the `window.va` shim unchanged

```html
<script>
    window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
</script>
```

This queues analytics calls before the deferred script loads — no changes needed here.

## Why This Works

- Ad blockers match on path patterns, not behavior. `/data/lib/script.js` looks like a generic library file.
- Vercel rewrites happen server-side — the client never sees `/_vercel/insights/` in the request.
- The `data-endpoint` attribute ensures pageview POSTs also go through the proxy path.

## Prevention / Best Practices

- **Choose a boring, generic path.** Avoid `/analytics/`, `/stats/`, `/tracking/`, `/metrics/` — these are on filter lists too. Something like `/data/lib/` or `/assets/vendor/` is less likely to be flagged.
- **Use full URLs in rewrite destinations.** Relative paths like `/_vercel/insights/:match*` silently fail for this use case.
- **Test with an ad blocker enabled.** Open DevTools → Network tab → filter by your path → confirm 200 response, not blocked.
- **This applies to any client-side analytics.** The same proxy pattern works for Plausible, PostHog, or any analytics script that gets blocked.

## References

- [Solving Vercel Analytics Blocked by AdBlock](https://kai.bi/post/vercel-kill-adblock)
- [Vercel Analytics blocked by AdBlockers — GitHub Issue #137](https://github.com/vercel/analytics/issues/137)
- [Analytics Rewrites to Bypass Ad Blockers](https://webreaper.dev/posts/analytics-rewrites/)
