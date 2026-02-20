# Brainstorm: Add Website CTA to Daily Digest Email

**Date:** 2026-02-20
**Status:** Ready for planning

## What We're Building

Add a prominent call-to-action button and clickable header to the daily digest email that drives readers to the website at `ai-venture-digest.vercel.app`.

Currently the email has **zero links to the website** — readers see article titles linking to original sources, plus Mailchimp's unsubscribe/archive links. The website offers a significantly richer experience (embedded videos, quick wins section, podcast players, theme toggle, visual card layouts) that email readers don't know about.

## Why This Approach

**Goal:** Drive traffic from email to website so readers discover the full experience.

**Chosen approach:** CTA button below the stats bar + clickable header title.

- **CTA button** — Placed right below the stats bar (top of email, before articles). Uses the existing blue-purple gradient (`#4a9eff` → `#8b5cf6`). Text: "View Full Digest on the Web →". High visibility since most readers don't scroll the entire email.
- **Clickable header** — The "AI Venture Digest" title in the dark header becomes a link to the website. Subtle second touchpoint for readers who instinctively click logos/brand names.

**Why not other approaches:**
- Footer-only link: Too low visibility, footer engagement is minimal
- Per-category links: Clutters the email, adds noise between articles
- Single button only: Missed the low-effort win of making the header clickable

## Key Decisions

1. **Placement:** Top of email, below stats bar — maximizes visibility
2. **CTA copy:** "View Full Digest on the Web" — straightforward, sets expectations
3. **Style:** Match existing email gradient (`#4a9eff` → `#8b5cf6`) for brand consistency
4. **Header link:** Make "AI Venture Digest" title text clickable (link to website)
5. **Target URL:** `https://ai-venture-digest.vercel.app`
6. **Plain text version:** Include the URL as a plain text line (no button styling possible)

## Scope

**In scope:**
- Add CTA button HTML to `generate_newsletter_html()` in `newsletter.py`
- Make header title a clickable link
- Add website URL to plain text version (`generate_newsletter_text()`)

**Out of scope:**
- UTM tracking parameters (can add later)
- A/B testing different CTA copy
- Adding more sections to the email (quick wins, podcasts, etc.)
- Redesigning the email layout

## Open Questions

- Should the button link include UTM parameters for analytics tracking? (Can defer)
- Should the website URL be configurable in `config.json` or hardcoded? (Lean toward config)
