# AI Venture Digest

A fully automated AI news aggregation and newsletter system designed for venture builders. Start your day with a curated 30-minute briefing on AI developments that matter.

## Features

- **Morning ritual structure**: Challenges, Top 5 reads, Video, Quick hits, Tool spotlight
- **Multi-source aggregation**: RSS feeds, Hacker News, Reddit
- **Smart curation**: Filters by engagement, source reputation, recency, and relevance
- **Daily email digest**: Mailchimp integration for subscribers
- **Auto-deployed**: GitHub Actions + Vercel for hands-free operation

---

## Quick Deploy to Vercel

### 1. Push to GitHub

```bash
cd ai-updates
git init
git add .
git commit -m "Initial commit"
gh repo create ai-venture-digest --public --push
```

### 2. Deploy to Vercel

```bash
vercel
```

Follow the prompts. Your site will be live at `https://your-project.vercel.app`

### 3. Add Environment Variables

In Vercel Dashboard → Settings → Environment Variables, add:

| Variable | Description |
|----------|-------------|
| `MAILCHIMP_API_KEY` | Your Mailchimp API key |
| `MAILCHIMP_LIST_ID` | Your Mailchimp audience/list ID |
| `MAILCHIMP_REPLY_TO` | Reply-to email for newsletters |
| `CRON_SECRET` | (Optional) Secret to protect cron endpoint |

### 4. Enable GitHub Actions

In your GitHub repo → Settings → Secrets → Actions, add the same secrets:
- `MAILCHIMP_API_KEY`
- `MAILCHIMP_LIST_ID`
- `MAILCHIMP_REPLY_TO`

The GitHub Action will run daily at 7 AM UTC to fetch content and send the newsletter.

---

## Getting Mailchimp Credentials

1. **API Key**:
   - Go to [Mailchimp](https://mailchimp.com) → Account → Extras → API Keys
   - Create a new key and copy it (format: `xxxxxxxx-us1`)

2. **List/Audience ID**:
   - Go to Audience → Settings → Audience name and defaults
   - Find the "Audience ID" at the bottom

---

## Project Structure

```
ai-updates/
├── index.html              # Main web interface (morning ritual)
├── config.json             # Source & filter configuration
├── vercel.json             # Vercel deployment config
├── data/
│   └── articles.json       # Curated articles (auto-updated)
├── api/
│   └── cron/
│       └── fetch.py        # Vercel serverless cron job
├── scripts/
│   ├── fetcher.py          # Content fetcher & curator
│   ├── newsletter.py       # Newsletter generator
│   └── run_daily.py        # Local automation script
└── .github/
    └── workflows/
        └── daily-fetch.yml # GitHub Actions daily job
```

---

## Local Development

### Run the fetcher manually
```bash
python3 scripts/fetcher.py
```

### Generate newsletter (without sending)
```bash
python3 scripts/newsletter.py
```

### Run full pipeline
```bash
python3 scripts/run_daily.py
```

### View the site locally
Just open `index.html` in your browser.

---

## Customization

### Add/remove sources
Edit `config.json` → `sources` → `rss_feeds`

### Adjust curation weights
Edit `config.json` → `filters`

### Change newsletter timing
Edit `.github/workflows/daily-fetch.yml` → `cron` schedule

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  GitHub Actions │────▶│  fetcher.py      │────▶│  articles.json  │
│  (daily cron)   │     │  (fetch+curate)  │     │  (committed)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │                        │
                                ▼                        ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  newsletter.py   │     │  Vercel         │
                        │  (generate+send) │     │  (static host)  │
                        └──────────────────┘     └─────────────────┘
                                │                        │
                                ▼                        ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Mailchimp       │     │  index.html     │
                        │  (email send)    │     │  (web view)     │
                        └──────────────────┘     └─────────────────┘
```

---

## License

MIT - do whatever you want with it!
