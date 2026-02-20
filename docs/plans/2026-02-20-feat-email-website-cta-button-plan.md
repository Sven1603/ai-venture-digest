---
title: "feat: Add website CTA button to daily digest email"
type: feat
date: 2026-02-20
---

# Add Website CTA Button to Daily Digest Email

## Overview

Add a prominent call-to-action button and clickable header to the daily digest email that drives readers to `https://ai-venture-digest.vercel.app`. The email currently has zero links to the website — readers can't discover the richer web experience (videos, quick wins, podcasts).

## Proposed Solution

Two visual changes to the email + one config addition:

1. **Clickable header** — Wrap the "AI Venture Digest" `<h1>` in an `<a>` tag linking to the website
2. **CTA button row** — New table row between the stats bar and main content with a styled button: "View Full Digest on the Web →"
3. **Plain text URL** — Add the website URL to the plain text email version (header area + footer)
4. **Config entry** — Add `website_url` to the `newsletter` section of `config.json` so the URL isn't hardcoded

## Acceptance Criteria

- [x] ~~`config.json` has `"website_url"` in the `newsletter` section~~ (Review decision: hardcoded as `WEBSITE_URL` constant instead)
- [x] Email header title "AI Venture Digest" links to the website URL
- [x] A styled CTA button appears between the stats bar and main content
- [x] CTA button uses flat `background-color: #4a9eff` with `linear-gradient` as progressive enhancement (Outlook fallback)
- [x] Plain text version includes the website URL after the header ~~and in the footer~~ (Review decision: footer already has "View in browser")
- [x] Button text reads "View Full Digest on the Web →"
- [x] Existing email layout and styling is not broken

## Implementation Details

### `config.json`

Add to the `newsletter` object (around line 97):

```json
"website_url": "https://ai-venture-digest.vercel.app"
```

### `scripts/newsletter.py` — Read `website_url` from config

At the top of both `generate_newsletter_html()` and `generate_newsletter_text()`, read the URL with a fallback:

```python
website_url = config.get('newsletter', {}).get('website_url', '')
```

If empty, skip the CTA button and header link (don't crash). This keeps backwards compatibility with older configs.

### `scripts/newsletter.py` — `generate_newsletter_html()`

**Change 1: Clickable header** (line ~129)

Wrap the existing `<h1>` in an `<a>` tag:

```html
<a href="{website_url}" style="color: #fff; text-decoration: none;">
  <h1 style="color: #fff; font-size: 24px; margin: 0; font-weight: 700;">
    AI Venture Digest
  </h1>
</a>
```

**Change 2: CTA button row** (insert between stats bar ~line 164 and main content ~line 166)

New `<tr>` with a centered, full-width button:

```html
<tr>
  <td style="background: #12121a; padding: 0 32px 20px 32px; text-align: center;">
    <a href="{website_url}"
       style="display: inline-block; background-color: #4a9eff;
              background: linear-gradient(135deg, #4a9eff, #8b5cf6);
              color: #ffffff; font-size: 15px; font-weight: 600;
              padding: 12px 28px; border-radius: 8px;
              text-decoration: none;">
      View Full Digest on the Web &rarr;
    </a>
  </td>
</tr>
```

Notes:
- `background-color: #4a9eff` is the fallback for Outlook (which ignores `linear-gradient`)
- `background: linear-gradient(...)` overrides in modern clients
- Matches the stats bar background (`#12121a`) so it looks like part of the same section

### `scripts/newsletter.py` — `generate_newsletter_text()`

**Change 3:** Add URL after header banner (after the empty line ~line 214):

```
View full digest: https://ai-venture-digest.vercel.app
```

**Change 4:** Add URL in footer (after tagline ~line 227):

```
Website: https://ai-venture-digest.vercel.app
```

### Email Client Compatibility Note

From learnings: `linear-gradient` on `background` is not supported in Outlook on Windows. The implementation uses `background-color` as a flat fallback before `background: linear-gradient(...)` — modern clients use the gradient, Outlook shows solid blue. This is standard progressive enhancement for HTML emails.

## References

- Brainstorm: `docs/brainstorms/2026-02-20-email-website-cta-brainstorm.md`
- Newsletter generator: `scripts/newsletter.py:40-231`
- Config: `config.json:91-98` (newsletter section)
- Learnings on field contracts: `docs/solutions/runtime-errors/uncommitted-config-after-rewrite.md`
