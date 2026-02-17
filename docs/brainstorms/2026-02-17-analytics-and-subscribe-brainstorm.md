# Brainstorm: Analytics & Working Subscribe Button

**Date:** 2026-02-17
**Status:** Ready for planning

## What We're Building

Two features to close operational gaps in the site:

1. **Working subscribe button** — Replace the stub `alert()` with an actual Mailchimp integration so visitors can sign up for the newsletter
2. **Basic analytics** — Add page view tracking so we can see how many people visit the site

## Why This Approach

### Subscribe: Vercel serverless + Mailchimp API
- Already have Mailchimp credentials (`MAILCHIMP_API_KEY`, `MAILCHIMP_LIST_ID`) in Vercel env
- Already have a serverless function pattern in `api/cron/fetch.py` to follow
- Double opt-in (`status: "pending"`) — Mailchimp handles the confirmation email automatically
- Honeypot field for basic bot protection without user friction
- No new dependencies — `urllib.request` + stdlib only

### Analytics: Vercel Analytics
- Already hosted on Vercel — zero backend work
- Free tier covers our scale (2.5k events/mo)
- Dashboard gives us: page views, unique visitors, referrers, top pages, countries
- Single script tag addition to `index.html`

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Analytics provider | Vercel Analytics | Already on Vercel, free, zero config |
| Subscribe backend | Vercel serverless function (`api/subscribe.py`) | Keeps API key server-side, follows existing pattern |
| Opt-in type | Double opt-in | Better deliverability, GDPR-friendly, industry standard |
| Bot protection | Honeypot field | Simple, no third-party, no user friction |
| Subscriber count display | Mailchimp dashboard only | Keep site simple, no extra endpoint needed |
| Mailchimp HTTP client | `urllib.request` | Matches existing codebase, no external deps |

## Scope

### In scope
- `api/subscribe.py` — POST endpoint that adds email to Mailchimp list
- Update `index.html` subscribe function to call the endpoint
- Honeypot hidden field in subscribe modal
- Success/error/already-subscribed UI feedback
- Vercel Analytics script tag in `index.html`

### Out of scope
- Subscriber count on site (check Mailchimp dashboard instead)
- Custom analytics dashboard or roll-your-own tracking
- Rate limiting (rely on Mailchimp's built-in abuse detection for now)
- reCAPTCHA or other heavy bot protection

## Open Questions

- None — ready to plan and implement.
