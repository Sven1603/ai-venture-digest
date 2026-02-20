---
title: "feat: Add table of contents bar with scroll spy and sliding pill indicator"
type: feat
date: 2026-02-20
brainstorm: docs/brainstorms/2026-02-20-table-of-contents-sidebar-brainstorm.md
---

# feat: Add table of contents bar with scroll spy and sliding pill indicator

## Overview

Add a sticky horizontal TOC bar to `index.html` that shows all visible page sections, highlights the active one with a smoothly animated sliding pill, and lets users jump to any section. Works at all screen sizes — no separate sidebar/bar modes.

## Problem Statement / Motivation

The digest page has 8 content sections. On a full day of content, users must scroll through a long page with no way to jump ahead or see what's below. A TOC solves three problems:

1. **Navigation** — click to jump to any section
2. **Orientation** — always know where you are on the page
3. **Discovery** — see all available section types at a glance

## Proposed Solution

### Layout: Sticky Horizontal Bar

A single horizontal bar (`position: sticky`) pinned below the sticky header at all screen sizes. No sidebar, no body layout changes, no new breakpoints.

```
┌──────────────────────────────┐
│  Header (sticky)             │
├──────────────────────────────┤
│ [● Quick Wins] [Podcast] [Must Reads] [Tutorial] [More...] │ ← sticky bar
├──────────────────────────────┤
│                              │
│  Today's Quick Wins          │
│  ┌───┐ ┌───┐ ┌───┐          │
│  │   │ │   │ │   │          │
│  └───┘ └───┘ └───┘          │
│                              │
│  Featured Podcast            │
│  ...                         │
└──────────────────────────────┘
```

This is simpler than a two-tier sidebar/bar layout because:
- No body padding changes (zero CLS)
- No second breakpoint (reuses existing 768px only)
- One pill animation axis (`translateX` only)
- One set of styles, one code path

### Section-to-Label Mapping

Short labels without emojis:

| Section ID | TOC Label |
|---|---|
| `quickWinsSection` | Quick Wins |
| `podcastSection` | Podcast |
| `mustReadsSection` | Must Reads |
| `videoSection` | Tutorial |
| `morePodcastsSection` | More Pods |
| `twitterSection` | X / Twitter |
| `launchesSection` | Launches |
| `quickHitsSection` | More Updates |

### Scroll Spy (IntersectionObserver)

- Observe all visible sections with `rootMargin: "-120px 0px -50% 0px"` — the negative top margin accounts for header + bar height, the negative bottom means a section becomes "active" when its top enters the upper half of the viewport.
- When multiple sections intersect, the most recently entered one wins (last `isIntersecting: true` entry in the callback).
- First section is active by default at page top.

### Sliding Pill Animation

A single absolutely-positioned `<div>` inside the `<nav>` that slides behind the active item:

- `transform: translateX(Npx)` + `width` matches the active item
- Position calculated from active item's `offsetLeft` and `offsetWidth`
- On initial load: pill appears instantly (no transition), then transitions are enabled via `requestAnimationFrame`
- On resize: recalculate pill position (simple, non-debounced — it's a 3-line function)

**Theme transition fix:** The existing `html.theme-ready *` wildcard sets `transition: background-color 0.3s, color 0.3s, border-color 0.3s` which clobbers any `transition` on the pill. Fix with a more specific selector:

```css
html.theme-ready .toc-pill {
    transition: transform 0.3s ease, width 0.3s ease,
                background-color 0.3s, color 0.3s, border-color 0.3s;
}
```

### Click-to-Scroll

When a user clicks a TOC item:
1. Set that item as active immediately and move the pill
2. Set `suppressObserver = true`
3. Call `section.scrollIntoView({ behavior: 'smooth' })`
4. `setTimeout(() => { suppressObserver = false }, 800)`

Simple timeout, no `scrollend` event, no state machine.

### Scroll Offset

Hardcoded in CSS — the header and bar heights are known design values:

```css
section { scroll-margin-top: 120px; }
```

If the header wraps differently at 768px, one media query override handles it.

## Technical Considerations

### CSS (~30 lines in `<style>` block)

- `.toc-nav` — `position: sticky`, `top` below header, horizontal flex, `overflow-x: auto`, hidden scrollbar, `z-index: 90`, background, border-bottom
- `.toc-item` — padding, color, font-size, border-radius, `flex-shrink: 0`, `text-decoration: none`
- `.toc-item.active` — brighter text color
- `.toc-pill` — `position: absolute`, background, border-radius, `z-index: -1`
- `html.theme-ready .toc-pill` — combined transform + theme transitions (specificity fix)
- `@media (prefers-reduced-motion: reduce)` — `transition: none` on pill
- `@media print` — `display: none` on `.toc-nav`
- All colors via existing CSS variables (`--bg-card`, `--bg-secondary`, `--text-primary`, `--text-secondary`, `--border`)

### JavaScript (~60 lines in `<script>` block)

Single `buildTOC()` function that handles everything:
- Section-to-label mapping (object literal)
- Query visible sections, skip `display: none`
- Build `<a>` items + pill `<div>`, append to `<nav>`
- `setActive(link)` — update classes, `aria-current`, move pill
- Click handler — `preventDefault`, set active, scroll, suppress observer
- IntersectionObserver — update active on scroll
- Resize listener — recalculate pill position
- Called at the end of `renderAll()`

### Accessibility

- `<nav aria-label="Table of contents">` wrapper
- Items are `<a href="#sectionId">` — semantic, focusable, free hash navigation
- `aria-current="true"` on the active item
- `prefers-reduced-motion` respected
- Hidden in print

### Stacking

| Element | z-index |
|---|---|
| Subscribe modal | 1000 (existing) |
| Sticky header | 100 (existing) |
| TOC bar | 90 (new) |

The bar sits naturally below the header in document flow. `z-index: 90` ensures scrolling content passes behind it.

## Acceptance Criteria

### Core
- [x] TOC bar renders after `renderAll()` with one item per visible section
- [x] Hidden sections (no data) are excluded
- [x] Clicking a TOC item smooth-scrolls to that section (heading visible below sticky elements)
- [x] Active section updates correctly as user scrolls
- [x] First section is active by default at page top

### Sliding Pill
- [x] Pill slides smoothly to the active item on section change
- [x] Pill appears instantly (no animation) on initial load
- [x] Pill does not bounce through intermediate sections on click-to-scroll
- [x] Pill recalculates correctly on window resize

### Bar Layout
- [x] Sticky bar pinned below the header at all screen sizes
- [x] Bar scrolls horizontally when items overflow
- [x] Touch targets are comfortable for tapping (~44px tall)

### Theme & Polish
- [x] Respects light/dark theme via CSS variables
- [x] Theme toggle transitions TOC smoothly
- [x] `prefers-reduced-motion` disables pill animation
- [x] Hidden in print
- [x] WCAG AA contrast in both themes

## Implementation Steps

### Step 1: HTML + CSS

Add to `index.html`:
- [x] Empty `<nav id="tocNav" class="toc-nav" aria-label="Table of contents">` after `</header>`, before `<main>`
- [x] CSS for `.toc-nav`, `.toc-item`, `.toc-pill`, media queries
- [x] `scroll-margin-top: 120px` on `section` elements
- [x] `html.theme-ready .toc-pill` specificity fix for transitions

### Step 2: JavaScript

Add `buildTOC()` function to the `<script>` block:
- [x] Build TOC items from visible sections
- [x] Wire up IntersectionObserver for scroll spy
- [x] Wire up click handlers with observer suppression
- [x] Wire up resize handler for pill repositioning
- [x] Call `buildTOC()` at the end of `renderAll()`

### Step 3: Test

- Both themes (light/dark)
- Mobile and desktop viewport widths
- Days with few sections visible vs. all 8
- Fast scrolling, click-to-scroll, resize

## References

- Brainstorm: `docs/brainstorms/2026-02-20-table-of-contents-sidebar-brainstorm.md`
- Existing sections and IDs: `index.html:805-873`
- CSS variables: `index.html:17-49`
- Responsive breakpoint: `index.html:753`
- Render pipeline: `index.html:1075-1089` (`renderAll()`)
- Section hiding logic: `index.html:1118, 1231, 1253-1254, 1280-1281`
- Theme transition system: `index.html:51-54` (`.theme-ready`)
- Light/dark theming learnings: `docs/solutions/ui-bugs/light-dark-mode-theming.md`
