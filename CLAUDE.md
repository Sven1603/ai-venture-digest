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
