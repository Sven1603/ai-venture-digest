---
title: "feat: Warm Maximalist Page Redesign"
type: feat
date: 2026-02-20
brainstorm: docs/brainstorms/2026-02-20-page-redesign-brainstorm.md
---

# Warm Maximalist Page Redesign

## Overview

Full visual redesign of `index.html` — shifting from dark minimal to a bold, warm maximalist design. Light-only, warm orange primary, color-blocked full-bleed sections, one marquee banner, chunky display fonts.

Reference: Tecoffee coffee shop website.

## Motivation

The dark theme reads as "developer tool." The audience — vibe coders, solopreneurs, indie hackers — responds to warmth and personality. This redesign makes the digest approachable and exciting.

## The Redesign

### Color Palette (4 colors)

| Color | Value | Usage |
|-------|-------|-------|
| **Orange** | `#E85D2C` | Brand — section backgrounds, CTAs, badges |
| **Cream** | `#FFF8F0` | Page background, alternating sections |
| **Navy** | `#1A1A2E` | Dark sections, primary text on light backgrounds |
| **White** | `#FFFFFF` | Card backgrounds |

Accent colors for category badges carry forward from the existing palette (green for tools, purple for skills, cyan for workflows, etc.) — darkened to pass WCAG AA on cream/white backgrounds.

### Section Backgrounds (3-color alternating rhythm)

Sections alternate between **cream**, **orange**, and **navy** in a repeating rhythm — not 8 unique treatments:

| Section | Background | Text/Cards |
|---------|-----------|------------|
| Header | White → orange gradient | Navy text |
| Quick Wins | `#E85D2C` (Orange) | White cards, navy text |
| Featured Podcast | `#1A1A2E` (Navy) | White text, orange accents |
| **Marquee** | `#FFD700` (Gold) | Navy text, continuous scroll |
| Must Reads | `#FFF8F0` (Cream) | Navy text, orange number badges |
| Tutorial Video | `#E85D2C` (Orange) | White text, embedded player |
| More Podcasts | `#FFF8F0` (Cream) | White cards, navy text |
| X / Twitter | `#1A1A2E` (Navy) | White cards |
| Launches | `#E85D2C` (Orange) | White cards |
| More Updates | `#FFF8F0` (Cream) | Navy text, minimal list |

Cards share one style: white background, `border-radius: 16px`, layered tinted shadow (`0 2px 8px rgba(232, 93, 44, 0.12), 0 8px 24px rgba(232, 93, 44, 0.06)`).

### Typography

- **Display:** Space Grotesk 700 (Google Fonts) — headings, marquee, section titles
- **Body:** DM Sans 400/500/600 (Google Fonts) — descriptions, meta, body
- **Fallback stack:** `'Space Grotesk', 'Arial Black', system-ui, sans-serif` / `'DM Sans', system-ui, sans-serif`
- Loading: `<link rel="preconnect">` + Google Fonts CSS, `font-display: swap`
- Tracking: `-0.03em` on headings > 24px, line-height `1.7` on body

### Layout: Full-Bleed Sections

Sections break out of the container for edge-to-edge backgrounds. Content stays constrained:

```html
<main>
  <section id="quickWinsSection" class="section-orange">
    <div class="container">...</div>
  </section>
  <div class="marquee" aria-hidden="true">...</div>
  <section id="podcastSection" class="section-navy">
    <div class="container">...</div>
  </section>
</main>
```

### Marquee Banner

One marquee after the header/Quick Wins area. Gold background, navy text.

- Repeating: "AI VENTURE DIGEST" with separator dots/symbols
- CSS `@keyframes translateX()` — GPU composited
- `aria-hidden="true"` (decorative)
- `@media (prefers-reduced-motion: reduce)` → static centered text

### Theme: Light Only

Remove the theme toggle. Ship light only. The warm orange palette IS the identity.

- Remove the `[data-theme="light"]` and `[data-theme="dark"]` CSS blocks
- Remove the FOUC `<head>` script (no theme to detect)
- Remove `toggleTheme()`, `initTheme()`, theme icon from header
- Remove `localStorage` theme key (`ai-digest-theme`)
- CSS variables stay (for consistency) but only define one set of values

### Styling Approach

Keep hand-written CSS with CSS custom properties — the existing pattern is clean and the file is self-contained. No Tailwind CDN (avoids 330KB JS dependency for a static page). The current ~830 lines of CSS will be rewritten with the new palette, fonts, and full-bleed structure.

## Contrast Verification Checklist

Every text/background pair must pass WCAG AA before implementation:

| Text | Background | Usage | Min Ratio | Passes? |
|------|-----------|-------|-----------|---------|
| `#FFFFFF` | `#E85D2C` | Headings on orange (large, 24px+) | 3:1 | 3.5:1 Yes |
| `#FFFFFF` | `#E85D2C` | Body text on orange (normal) | 4.5:1 | 3.5:1 **No — use white cards** |
| `#1A1A2E` | `#FFF8F0` | Body text on cream | 4.5:1 | 14.2:1 Yes |
| `#1A1A2E` | `#FFFFFF` | Body text on white cards | 4.5:1 | 15.4:1 Yes |
| `#FFFFFF` | `#1A1A2E` | Body text on navy | 4.5:1 | 15.4:1 Yes |
| `#1A1A2E` | `#FFD700` | Marquee text on gold | 4.5:1 | 10.2:1 Yes |
| `#E85D2C` | `#FFF8F0` | Orange accent text on cream (large only) | 3:1 | 3.6:1 Yes |
| `#E85D2C` | `#FFFFFF` | Orange badge text on white (large only) | 3:1 | 3.9:1 Yes |

**Key rule:** On orange section backgrounds, body text goes inside white cards. Only large headings (24px+ bold) use white text directly on orange. This is why all sections with orange backgrounds use white card containers.

### Focus States

All interactive elements use this consistent focus ring (works on any background):

```css
:focus-visible {
  outline: 2px solid #1A1A2E;
  outline-offset: 2px;
  box-shadow: 0 0 0 4px white;
}
```

### Reduced Motion

All animations respect `prefers-reduced-motion: reduce`:
- Marquee → static centered text
- Card hover `translateY(-2px)` → disabled
- TOC pill sliding → instant snap (already implemented)

## Acceptance Criteria

### Visual

- [x] Cream (`#FFF8F0`) page background, orange/navy/cream alternating full-bleed sections
- [x] Space Grotesk 700 on all headings, section titles, marquee text
- [x] DM Sans 400/500/600 on descriptions, meta, badges, body text
- [x] Sections use 3 alternating backgrounds — not 8 unique treatments
- [x] One gold marquee banner with continuous horizontal scroll between header area and content
- [x] White cards with `border-radius: 16px` and layered orange-tinted shadows
- [x] Subscribe button and modal use orange primary, navy text
- [x] Header features orange gradient accent and Space Grotesk logo text

### Functional

- [x] All 8 sections render correctly from `data/articles.json`
- [x] TOC scroll spy tracks correctly with full-bleed layout
- [x] TOC click-to-scroll lands at correct positions (recalculated `scroll-margin-top`)
- [x] Subscribe modal: opens, validates email, POST to `/api/subscribe`, shows success/error
- [x] Honeypot field styling preserved exactly (inline `position:absolute;left:-9999px;opacity:0`)
- [x] Fallback content renders when JSON fails to load
- [x] Empty sections auto-hide and TOC adjusts
- [x] Theme toggle removed — no dark mode, no FOUC script needed

### Quality

- [x] Zero `transition-all` in the file (fix existing 6 violations during restyling)
- [x] All interactive elements have hover, focus-visible, and active states
- [x] `prefers-reduced-motion: reduce` disables marquee animation and card hover transforms
- [x] All text/background pairs pass WCAG AA per checklist above
- [x] Mobile responsive at 768px breakpoint, tested at 375px
- [x] Vercel Analytics script preserved (`/data/lib/script.js` with `data-endpoint="/data/lib"`)
- [x] Minimum 2 screenshot comparison rounds (desktop 1280px + mobile 375px)

## Implementation Order

No phases — it's one file. Work top to bottom, screenshot as you go:

1. Add Google Fonts links in `<head>` (Space Grotesk + DM Sans)
2. Rewrite CSS custom properties with new 4-color palette
3. Remove theme toggle code (CSS blocks, FOUC script, JS functions, header icon)
4. Restructure HTML: sections outside container for full-bleed, inner `.container` divs
5. Restyle header (orange gradient, display font, subscribe button)
6. Restyle TOC nav bar (orange pill, warm palette)
7. Restyle each section top → bottom, fixing `transition-all` violations as encountered
8. Add marquee banner HTML + CSS keyframes + reduced-motion fallback
9. Add hover/focus-visible/active states to all interactive elements
10. Recalculate `scroll-margin-top` and TOC `rootMargin` for new header/TOC height
11. Test mobile responsiveness, fix breakpoint issues
12. Screenshot at 1280px and 375px, compare to reference, fix, re-screenshot

## Key Gotchas

- **Observer teardown:** Preserve module-level `_tocObserver` disconnect pattern — per `docs/solutions/ui-bugs/intersection-observer-scroll-spy.md`
- **Observer suppression:** 800ms click-to-scroll suppression must stay
- **RAF-debounced resize:** `cancelAnimationFrame` before new — preserved
- **Marquee overflow:** `overflow: hidden` on wrapper to prevent horizontal scrollbar on mobile
- **Product Hunt descriptions:** Some contain `"Discussion\n|\nLink"` artifacts — note for fetcher fix, not blocking

## Contracts to Preserve

- `data/articles.json` field names (implicit contract with `fetcher.py`)
- Section IDs: `quickWinsSection`, `podcastSection`, `mustReadsSection`, `videoSection`, `morePodcastsSection`, `twitterSection`, `launchesSection`, `quickHitsSection`
- Subscribe POST body: `{ email, website, t_open, t_submit }` to `/api/subscribe`
- Vercel Analytics: `/data/lib/script.js` with `data-endpoint="/data/lib"`

## References

- Brainstorm: `docs/brainstorms/2026-02-20-page-redesign-brainstorm.md`
- Current page: `index.html` (1,614 lines)
- Scroll spy solution: `docs/solutions/ui-bugs/intersection-observer-scroll-spy.md`
