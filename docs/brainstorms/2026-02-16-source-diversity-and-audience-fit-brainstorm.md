---
title: Source diversity and audience fit
date: 2026-02-16
status: decided
---

# Source diversity and audience fit

## What We're Building

Two changes to improve digest quality:

1. **Lower `max_per_source` from 3 to 2** — more unique sources in the 30-article output
2. **Expand RSS feeds** — restore dropped mainstream AI sources + add new ones suited to the audience

## Target Audience

**Not software engineers.** The audience is:
- Vibe coders (building with AI tools, not writing frameworks)
- Marketing people using AI for content/automation
- Solopreneurs and indie hackers shipping MVPs
- Non-technical people who want to follow AI practically

**Content should be:** accessible, practical, tool-focused, business-oriented
**Content should NOT be:** academic papers, deep engineering, CUDA kernels, ML research

## Key Decisions

### 1. max_per_source: 3 → 2

Current: 12 unique sources in 30 articles (8 sources hitting the cap of 3)
Expected: ~18-20 unique sources, more variety per digest

### 2. Sources to restore (from old config, audience-appropriate)

- **TechCrunch AI** — accessible AI news, startup coverage (reputation: 0.9)
- **The Verge AI** — consumer-friendly AI coverage (reputation: 0.85)
- **OpenAI Blog** — product announcements relevant to everyone (reputation: 1.0)
- **Google AI Blog** — Gemini updates, consumer AI (reputation: 1.0)
- **Anthropic Blog** — Claude updates, direct product relevance (reputation: 1.0)

### 3. Sources to NOT restore

- **Ars Technica AI** — too technical for audience
- **MIT Tech Review AI** — too academic/research-heavy

### 4. New sources to consider (practical/business/creator focus)

- **Lenny's Newsletter** — product management + AI (was in old config, dropped)
- **Ben's Bites** — daily AI newsletter, accessible, tool-focused
- **The Neuron** — AI newsletter for non-technical audience
- **Matt Wolfe / AI Tool Report** — AI tool reviews and demos
- **Every.to** — AI for knowledge workers and creators

### 5. YouTube channels to review

Current channels include Sam Witteveen and James Briggs — both very LangChain/engineering focused. Consider swapping or deprioritizing in favor of more accessible creators.

## Open Questions

- Should we adjust the `topics` list to be less engineering-heavy? (currently includes "rag", "embeddings", "vector database" which are engineering terms)
- Should YouTube tutorial channels be filtered for accessibility level?
