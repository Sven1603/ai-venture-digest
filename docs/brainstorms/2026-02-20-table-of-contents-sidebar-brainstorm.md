# Table of Contents Sidebar

**Date:** 2026-02-20
**Status:** Ready for planning

## What We're Building

A navigational table of contents that shows all visible page sections and highlights the currently active one with a smoothly animated sliding pill. Lets users jump to any section with one click and always see where they are on the page.

**Desktop:** Fixed left sidebar alongside the main content column.
**Mobile (< 768px):** Horizontal scrolling bar pinned under the sticky header.

## Why This Approach

- **Left sidebar** keeps the content column undisturbed and is scannable at a glance
- **Horizontal bar on mobile** avoids the need for a drawer/overlay interaction — always visible, zero taps to access
- **Sliding pill animation** (CSS transforms) gives a fluid, modern feel without being flashy — similar to iOS segment controls or Vercel's nav tabs

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Desktop placement | Fixed left sidebar | Doesn't compete with content; always accessible |
| Mobile placement | Horizontal bar under header | Always visible, no extra interaction needed |
| Active indicator | Filled pill background | Clear, visible, works in both light/dark themes |
| Animation | Sliding + resizing pill via CSS transforms | Smooth, modern feel; GPU-accelerated; no JS animation library needed |
| Section detection | IntersectionObserver | Native API, performant, no scroll event throttling needed |
| Dynamic sections | Build TOC after render, skip hidden sections | Sections with `display: none` are excluded from TOC |

## Scope

### In scope
- TOC items derived from visible sections (8 possible sections, some conditionally hidden)
- Smooth scroll to section on click (offset for sticky header)
- Scroll spy via IntersectionObserver to track active section
- Sliding pill that animates position/size between active items
- Light/dark theme support via existing CSS variables
- Responsive: sidebar on desktop, horizontal bar on mobile

### Out of scope
- Nested/hierarchical TOC (sections are flat, no sub-items)
- Collapsible sidebar
- Reading progress bar
- Keyboard navigation within TOC

## Open Questions

None — ready for planning.
