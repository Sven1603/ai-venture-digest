---
title: "Expand source diversity and tune for non-technical audience"
type: feat
date: 2026-02-16
---

# Expand source diversity and tune for non-technical audience

## Overview

Lower the per-source cap from 3 to 2, restore mainstream AI blogs dropped in the fetcher rewrite, add new accessible sources, and adjust the topics list for the target audience: vibe coders, marketing people, and solopreneurs — not software engineers.

Brainstorm: `docs/brainstorms/2026-02-16-source-diversity-and-audience-fit-brainstorm.md`

## Changes

### 1. `config.json` — filters

- [ ] Change `max_per_source` from `3` to `2`

### 2. `config.json` — RSS feeds to restore

These were in the original config, are audience-appropriate, and have verified feed URLs:

- [ ] `TechCrunch AI` — `https://techcrunch.com/category/artificial-intelligence/feed/` (reputation: 0.9, type: news)
- [ ] `The Verge AI` — `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` (reputation: 0.85, type: news)
- [ ] `OpenAI Blog` — `https://openai.com/blog/rss.xml` (reputation: 1.0, type: product)
- [ ] `Google AI Blog` — `https://blog.google/technology/ai/rss/` (reputation: 1.0, type: product)
- [ ] `Anthropic Blog` — `https://www.anthropic.com/rss.xml` (reputation: 1.0, type: product)
- [ ] `Lenny's Newsletter` — `https://www.lennysnewsletter.com/feed` (reputation: 0.85, type: product)

**Not restoring** (too technical for audience):
- Ars Technica AI
- MIT Tech Review AI

### 3. `config.json` — new RSS feeds to add

Verified working feed URLs:

- [ ] `Ben's Bites` — `https://www.bensbites.com/feed` (reputation: 0.9, type: news) — accessible AI newsletter covering tools and trends
- [ ] `The Neuron` — `https://rss.beehiiv.com/feeds/N4eCstxvgX.xml` (reputation: 0.85, type: news) — daily AI for non-technical audience, 600K+ subscribers

### 4. `config.json` — topics list

Replace engineering-heavy terms with audience-appropriate ones.

**Remove** (too technical):
- `"rag"`, `"embeddings"`, `"vector database"`, `"langgraph"`

**Keep** (relevant to audience):
- `"claude code"`, `"cursor"`, `"ai coding"`, `"workflow automation"`, `"n8n"`, `"make"`
- `"langchain"`, `"ai agents"`, `"prompt engineering"`, `"ai tools"`
- `"saas"`, `"mvp"`, `"indie hacker"`, `"solopreneur"`
- `"remotion"`, `"video automation"`, `"ai marketing"`, `"content automation"`

**Add** (audience-relevant):
- `"vibe coding"`, `"no-code"`, `"low-code"`, `"ai writing"`, `"chatgpt"`, `"gemini"`, `"ai productivity"`

### 5. `config.json` — YouTube channels (review)

Sam Witteveen and James Briggs are heavily LangChain/engineering focused. Consider lowering their reputation scores so they don't dominate tutorials:

- [ ] `Sam Witteveen` reputation: 0.9 → 0.75
- [ ] `James Briggs` reputation: 0.9 → 0.75

## Acceptance Criteria

- [ ] `max_per_source` is 2
- [ ] At least 14 RSS feeds configured (currently 6)
- [ ] Topics list has no deep engineering terms (rag, embeddings, vector database)
- [ ] Topics list includes accessible terms (vibe coding, no-code, chatgpt)
- [ ] Fetcher runs successfully with new config
- [ ] Output has 15+ unique sources (currently ~12)

## Files to change

1. **`config.json`** — all changes (filters, sources, topics)

No code changes needed — `fetcher.py` already reads everything from config.
