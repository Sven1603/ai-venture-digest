# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Venture Digest — an automated AI news aggregation and newsletter system for venture builders. Fetches content from RSS feeds, YouTube, podcasts, Twitter/X (via Nitter), Hacker News, and Reddit, then scores/curates it into a daily briefing delivered via web and Mailchimp email.

## Commands

```bash
# Fetch and curate content
python3 scripts/fetcher.py

# Generate newsletter (requires MAILCHIMP_* env vars to send)
python3 scripts/newsletter.py

# Run full pipeline (fetch → newsletter)
python3 scripts/run_daily.py

# View site locally — open index.html in browser (loads data/articles.json)
```

No external Python dependencies — uses only stdlib (`urllib`, `xml.etree`, `json`, `pathlib`, etc.).

## Architecture

**Pipeline:** GitHub Actions (daily 7 AM UTC) or Vercel cron → `fetcher.py` → `data/articles.json` → `newsletter.py` → Mailchimp + `templates/` → git commit + push → Vercel serves `index.html`

Key components:
- **`config.json`** — Single source of truth for all content sources (with reputation scores), keyword topics, filter weights, and thresholds. Edit this to add/remove sources or tune curation.
- **`scripts/fetcher.py`** (~770 lines) — Fetches from 6+ source types, applies 3-layer content filtering (`is_actionable_content`, `is_tool_content`, `is_podcast_relevant`), calculates weighted scores (reputation 25%, relevance 30%, recency 20%, engagement 25%), selects quick wins and top articles, writes `data/articles.json`.
- **`scripts/newsletter.py`** (~380 lines) — Reads `data/articles.json`, generates Mailchimp-compatible HTML email + plain text, creates campaign via Mailchimp API, saves template to `templates/`.
- **`scripts/run_daily.py`** — Orchestrator that runs fetcher then newsletter sequentially.
- **`api/cron/fetch.py`** — Vercel serverless function handler for the `/api/cron/fetch` cron endpoint (alternative trigger to GitHub Actions).
- **`index.html`** — Dark-themed single-page app that dynamically loads `data/articles.json`. Vanilla JS/CSS, no framework.

## Environment Variables

Required for newsletter sending (set in GitHub Actions secrets and/or Vercel):
- `MAILCHIMP_API_KEY` — format: `xxxxxxxx-usXX`
- `MAILCHIMP_LIST_ID` — Mailchimp audience ID
- `MAILCHIMP_REPLY_TO` — reply-to email address

Optional:
- `CRON_SECRET` — protects Vercel cron endpoint
- `NEWSLETTER_SEND_NOW` — set `true` to send immediately instead of scheduling

## Content Scoring

The scoring algorithm in `fetcher.py` (`calculate_score`) uses weighted factors configurable in `config.json` under `filters`. Content must be < 72 hours old. Tutorials and how-to content score highest. Hard excludes: nature docs, academic papers, funding news, roundups.

## Deployment

Two automated paths (both run daily at 7 AM UTC):
1. **GitHub Actions** (`.github/workflows/daily-fetch.yml`) — runs pipeline, commits updated `data/` back to repo
2. **Vercel Cron** (`vercel.json`) — hits `/api/cron/fetch` serverless function

Static hosting via Vercel. Deploy with `vercel --prod --yes` or use `deploy.sh` for one-click setup.

### Vercel Python Functions

Vercel auto-detects Python for files in `api/`. Do **not** set `"runtime"` in the `functions` block of `vercel.json` — the built-in Python runtime requires no runtime config. Pin the Python version via `.python-version` in the project root (currently `3.12`). Supported versions: 3.12, 3.13, 3.14.

### CI Debugging

The GitHub Actions workflow checks out the commit that was latest when the scheduled run triggered — not necessarily the current HEAD. If a CI fix is pushed after the cron fires, it won't take effect until the next run. Use `gh workflow run "Daily AI Digest Fetch"` to trigger a manual run against the latest commit.

## Frontend work rules

Use these rules whenever visual frontend changes are requested

### Always Do First
- **Invoke the `frontend-design` skill** before writing any frontend code, every session, no exceptions.

### Reference Images
- If a reference image is provided: match layout, spacing, typography, and color exactly. Swap in placeholder content (image via `https://placehold.co, generic copy). Do not improve or add to the design.
- If no reference image: design from scratch, with high craft (see guardrails below).
- If multiple reference images are provided: find the best mix of both worlds.
- Screenshot your output, compare against reference, fix mismatches, re-screenshot. Do at least 2 comparison rounds. Stop only when no visible differences remain or user says so.

### Local Server
- **Always serve on localhost** - never screenshot a `file:///` URL.
- Start the dev server (it runs at `http://localhost:8000`)
- If the server is already running, don't start a second instance

### Screenshot workflow
- Puppeteer is installed at `/Users/sven/.nvm/versions/node/v22.17.1/lib/node_modules/puppeteer`. Chrome cache is at `/Users/sven/.cache/puppeteer/chrome/mac_arm-145.0.7632.77/chrome-mac-arm64/`.
- **Always screenshot from localhost:** `node screenshot.mjs http://localhost:8000`
- Screenshots are saved automatically to `./temporary screenshots/screenshot-N.png` (auto incremented, never overwritten).
- Optional label suffix: `node screenshot.mjs http://localhost:8000 label` -> saves as `screenshot-N-label.png`
- `screenshot.mjs` lives in the project root. Use it as-is.
- After screenshotting, read the PNG from `temporary screenshots/` with the Read tool - Claude can see and analyze the image directly.
- When comparing, be specific: "heading is 32px but reference shows ~24px", "card gap is 16px but should be 24px"
- Check: spacing/padding, font size/weight/line-height, colors (exact-hex), alignment, border-radius, shadows, image sizing

### Output Defaults
- Single `index.html` file, all styles inline, unless user says otherwise
- Tailwind CSS via CDN: `<script src="https://cdn.tailwindcss.com"></script>`
- Placeholder images: `https://placehold.co/WIDTHxHEIGHT`
- Mobile-first responsive

## Brand Assets
- Always check the `brand_assets/` folder before designing. It may contain logos, color guides, style guides, or images.
- If assets exist there, use them. Do not use placeholders where real assets are available.
- If a logo is present, use it. If a color palette is defined, use those exact values — do not invent brand colors.

## Anti-Generic Guardrails
- **Colors:** Never use default Tailwind palette (indigo-500, blue-600, etc.). Pick a custom brand color and derive from it.
- **Shadows:** Never use flat `shadow-md`. Use layered, color-tinted shadows with low opacity.
- **Typography:** Never use the same font for headings and body. Pair a display/serif with a clean sans. Apply tight tracking (`-0.03em`) on large headings, generous line-height (`1.7`) on body.
- **Gradients:** Layer multiple radial gradients. Add grain/texture via SVG noise filter for depth.
- **Animations:** Only animate `transform` and `opacity`. Never `transition-all`. Use spring-style easing.
- **Interactive states:** Every clickable element needs hover, focus-visible, and active states. No exceptions.
- **Images:** Add a gradient overlay (`bg-gradient-to-t from-black/60`) and a color treatment layer with `mix-blend-multiply`.
- **Spacing:** Use intentional, consistent spacing tokens — not random Tailwind steps.
- **Depth:** Surfaces should have a layering system (base → elevated → floating), not all sit at the same z-plane.

## Hard Rules
- Do not add sections, features, or content not in the reference
- Do not stop after one screenshot pass
- Do not use `transition-all`
- Do not use default Tailwind blue/indigo as primary color