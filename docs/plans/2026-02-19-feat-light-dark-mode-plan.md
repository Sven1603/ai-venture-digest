---
title: Add light and dark mode
type: feat
date: 2026-02-19
reviewed: true
reviewers: dhh-rails-reviewer, kieran-typescript-reviewer, code-simplicity-reviewer
---

# Add Light and Dark Mode

## Overview

Add theme switching to `index.html` — default to OS preference (`prefers-color-scheme`), allow manual override via a toggle button in the header, and persist the choice in `localStorage`.

## Proposed Solution

Single-file change to `index.html`. The site already uses CSS custom properties for all colors, so theming is just a matter of overriding those variables under a `[data-theme="light"]` selector.

### CSS Changes

1. **Add `/* Dark theme (default) */` comment above `:root`** — makes intent explicit that `:root` IS the dark theme and must not be duplicated into a `[data-theme="dark"]` block.

2. **Add `[data-theme="light"]` block** overriding only the neutral variables (9 vars). Keep accent colors unchanged initially — they are saturated enough to read on light backgrounds. Add accent overrides only if visual testing reveals contrast issues.

```css
[data-theme="light"] {
    --bg-primary: #faf8f5;
    --bg-secondary: #f0ede8;
    --bg-card: #ffffff;
    --bg-card-hover: #f5f2ed;
    --text-primary: #1a1a2e;
    --text-secondary: #4a4a5e;
    --text-muted: #7a7a8e;
    --border: #e0ddd8;
    --border-light: #d0cdc8;
}
```

If visual testing shows accent contrast issues (especially `--accent-blue` and `--accent-green` on small label text), darken them to WCAG AA-compliant alternatives:
- `--accent-blue`: `#2563eb` (contrast ~5.3:1 on #faf8f5)
- `--accent-green`: `#047857` (contrast ~5.1:1 on #faf8f5)

3. **Add `.theme-toggle` button styles** — 40x40px bordered icon button matching existing header button patterns.

4. **Visually test `rgba()` badge/icon backgrounds** — There are ~15 hardcoded `rgba()` values at 0.15 alpha (badge backgrounds at lines 348-355, icon backgrounds at lines 189-191, 385, 507, podcast gradient at line 232). These tint a dark surface subtly. On a white surface they may appear washed out. Test during implementation and add light-mode overrides only if needed.

5. **Smooth theme transition** (polish) — Add `transition: background-color 0.3s, color 0.3s` scoped to a `.theme-ready` class on `<html>`, applied by JS after initial load. Prevents jarring flash on toggle while avoiding transition during FOUC prevention.

### Hardcoded Colors Audit

These hardcoded hex/rgba values are intentionally theme-agnostic — no overrides needed:

| Value | Location | Reason |
|-------|----------|--------|
| `#000` | `.video-container` (line 462) | Video backgrounds stay dark |
| `rgba(0,0,0,0.85)` | `.modal-overlay` (line 647) | Dark overlay dims content on both themes |
| `#ef4444` | `.category-badge.launch`, `.launch-card:hover` (lines 355, 379) | Brand red, legible on both |
| `#1DA1F2` | `.twitter-post:hover`, `.twitter-avatar` (lines 554, 560) | Twitter brand blue |
| `#ef4444` / `#10b981` | `showSubscribeMessage()` JS (line 1322) | Error red / success green, legible on both |

### HTML Changes

Add a theme toggle button in `.header-right`, between the date and subscribe button:

```html
<button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle theme">
    <span id="themeIcon"></span>
</button>
```

### JavaScript Changes

Two functions only. The FOUC `<head>` script is the single source of truth for initial theme detection — no duplication in the main script.

```javascript
// Sync toggle icon to current theme (called on load + after toggle)
function initTheme() {
    // Must match the localStorage key used in the <head> FOUC prevention script
    var theme = document.documentElement.getAttribute('data-theme');
    var icon = document.getElementById('themeIcon');
    if (icon) icon.textContent = theme === 'dark' ? '\u2600\uFE0F' : '\uD83C\uDF19';
    // Enable smooth transitions after initial render
    document.documentElement.classList.add('theme-ready');
}

function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme') || 'dark';
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    // Must match the localStorage key used in the <head> FOUC prevention script
    localStorage.setItem('ai-digest-theme', next);
    initTheme();
}
```

Call `initTheme()` at the top of the main `<script>` block (before `loadArticles()`) to sync the icon.

### Flash-of-unstyled-content (FOUC) prevention

Add a tiny inline script in `<head>` (before the `<style>` block) to set `data-theme` immediately:

```html
<script>
    (function() {
        var t = localStorage.getItem('ai-digest-theme');
        if (!t) t = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', t);
    })();
</script>
```

## Acceptance Criteria

- [x] Site defaults to OS `prefers-color-scheme` on first visit (no localStorage value)
- [x] Toggle button in header switches between light and dark mode
- [x] Theme choice persists in `localStorage` across page reloads
- [x] Light mode uses warm off-white palette (#faf8f5 base)
- [x] All sections render correctly in both themes (cards, modals, badges, gradients)
- [x] No flash of wrong theme on page load
- [x] Toggle icon shows sun in dark mode, moon in light mode
- [x] Mobile responsive — toggle fits in header at small viewports
- [x] Theme switch has smooth transition (no jarring flash)
- [x] Accent colors pass WCAG AA contrast on light background (darken if needed)

## Scope

- **In scope:** `index.html` only
- **Out of scope:** Newsletter email templates (separate HTML generation, email clients have limited CSS support)

## Gotchas

- Logo gradient and `.must-read-number` gradient stay the same (brand colors, not theme-dependent)
- The `localStorage` key `ai-digest-theme` must stay in sync between the `<head>` FOUC script and `toggleTheme()` — if one changes, both must change
- Remember to commit `index.html` after changes — CI will deploy stale code otherwise
- Start with neutral-only overrides; add accent overrides only after visual testing

## References

- Existing CSS variables: `index.html:9-25`
- Header layout: `index.html:733-748`
- Modal overlay: `index.html:640-651`
- rgba badge backgrounds: `index.html:348-355`
- Documented gotcha about uncommitted HTML: `docs/solutions/logic-errors/source-concentration-and-display-quality.md`
