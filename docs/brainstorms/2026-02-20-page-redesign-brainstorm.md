# Page Redesign: Warm Maximalist

**Date:** 2026-02-20
**Status:** Ready for planning

## What We're Building

A full visual redesign of the AI Venture Digest website (`index.html`), shifting from the current dark, minimal, developer-oriented aesthetic to a bold, playful, warm maximalist design inspired by the Tecoffee coffee shop website.

The redesign transforms the page into a vibrant, color-blocked experience where each content section feels like scrolling through a different "room" — each with its own personality, background color, and layout treatment.

## Reference

- **Primary inspiration:** Tecoffee website (attached image)
- **Key traits adopted:** Color blocking, marquee banners, chunky display typography, supersized emoji icons, full-page energy, section diversity

## Why This Approach

The current dark-themed design feels aimed at developers. The target audience — vibe coders, solopreneurs, marketing people, indie hackers — responds better to warmth, energy, and personality. A maximalist warm orange palette signals approachability and excitement about AI tools, not technical depth.

## Key Decisions

1. **Theme direction:** Light-first with bold colors. Dark mode is optional/deprioritized — the warm orange palette is the identity.

2. **Color palette:** Warm orange (`~#E8642C`) as the primary base/brand color. Electric accents (blue, teal, vivid green) layered on top for contrast and energy. Each section gets a distinct background color treatment.

3. **Playfulness level:** Full playful. Marquee text banners between sections. Chunky rounded display fonts for headings. Illustrated/decorative elements. Varied section backgrounds. Bold colored cards instead of subtle borders.

4. **Section structure:** Keep all 8+ existing sections (Quick Wins, Podcast, Must Reads, Tutorial, More Podcasts, X/Twitter, Launches, More Updates). Each section gets a unique visual treatment — different background colors, card styles, and layout variations.

5. **Typography:** Move away from system fonts. Pair a bold/chunky display font (headings) with a clean readable sans-serif (body). Tight tracking on large headings, generous line-height on body text.

6. **Card design:** Shift from dark translucent cards with subtle borders to bold colored backgrounds, rounded corners, and playful shadows. Cards should feel tactile and inviting.

7. **Marquee banners:** Horizontal scrolling text strips between major sections (like Tecoffee's repeating brand name banners). Use these to inject energy and visual rhythm between content blocks.

## Design Language Summary

| Element | Current | Redesign |
|---------|---------|----------|
| Base | Dark (#0a0a0f) | Light/warm cream or white |
| Primary color | Blue-purple gradient | Warm orange (#E8642C-ish) |
| Accents | Muted category colors | Electric blue, teal, vivid green |
| Typography | System fonts, uniform | Display + sans-serif pair |
| Cards | Dark bg, subtle borders | Bold colored backgrounds |
| Section breaks | Uniform dark sections | Color-blocked, each unique |
| Personality | Minimal, developer-y | Playful, warm, energetic |
| Interstitials | None | Marquee text banners |

## Open Questions

- Which specific display font to use? (e.g., Space Grotesk, Plus Jakarta Sans, Outfit, or something chunkier)
- Should the subscribe modal also get a full redesign or just a color update?
- Do we want any animated/decorative SVG elements (geometric shapes, squiggles) or keep it to color and type?
- Should the TOC sticky nav bar be restyled or replaced with a different navigation pattern?
- How to handle the theme toggle — keep it but deprioritize, or remove entirely?

## Constraints

- Must remain a single `index.html` file with inline styles (per project conventions)
- All content rendered dynamically from `data/articles.json` — no structural data changes
- Must stay responsive (mobile-first)
- No external JS frameworks — vanilla JS only
- Tailwind CSS via CDN is acceptable per CLAUDE.md
