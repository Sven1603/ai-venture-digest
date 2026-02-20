---
title: Light/dark mode theming with FOUC prevention and WCAG contrast
category: ui-bugs
module: index.html
tags: [theme, dark-mode, light-mode, css-variables, fouc, wcag, contrast, localStorage]
severity: medium
date: 2026-02-19
root_cause: Accent colors designed for dark backgrounds fail WCAG AA contrast on light backgrounds
---

# Light/Dark Mode Theming with FOUC Prevention and WCAG Contrast

## Symptom

Dark-only site with no theme switching. Users on light-preference OS settings or in bright environments had no alternative. Adding light mode naively causes two problems: flash of wrong theme (FOUC) on load, and accent colors that are unreadable on light backgrounds.

## Root Cause

1. **FOUC** — Theme logic in a deferred `<script>` runs after CSS paints, causing a visible flash from default dark to user-preferred light.
2. **Contrast failure** — Accent colors (#4a9eff blue, #10b981 green, #f59e0b orange, #06b6d4 cyan) were picked for dark backgrounds (~#1a1a24). On light backgrounds (#faf8f5), they fall below WCAG AA 4.5:1 contrast ratio (measured: 2.0:1 to 2.6:1).

## Solution

### 1. FOUC prevention — synchronous head script

Add an inline `<script>` in `<head>` **before** the `<style>` block. It runs synchronously before CSS parsing:

```html
<script>
    (function() {
        var t = localStorage.getItem('ai-digest-theme');
        if (!t) t = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', t);
    })();
</script>
```

### 2. CSS variable overrides — single selector, no duplication

`:root` IS the dark theme. Add only a `[data-theme="light"]` block — no `[data-theme="dark"]` block needed:

```css
[data-theme="light"] {
    --bg-primary: #faf8f5;
    --bg-secondary: #f0ede8;
    --bg-card: #ffffff;
    --bg-card-hover: #f5f2ed;
    --text-primary: #1a1a2e;
    --text-secondary: #4a4a5e;
    --text-muted: #7a7a8e;
    --accent-blue: #2563eb;
    --accent-green: #047857;
    --accent-orange: #d97706;
    --accent-cyan: #0891b2;
    --border: #e0ddd8;
    --border-light: #d0cdc8;
}
```

### 3. WCAG AA darkened accents

| Color | Dark mode | Light mode | Contrast on #faf8f5 |
|-------|-----------|------------|---------------------|
| Blue | #4a9eff | #2563eb | ~5.3:1 |
| Green | #10b981 | #047857 | ~5.1:1 |
| Orange | #f59e0b | #d97706 | ~4.6:1 |
| Cyan | #06b6d4 | #0891b2 | ~4.5:1 |
| Purple | #8b5cf6 | unchanged | ~4.0:1 (bold text OK) |
| Pink | #ec4899 | unchanged | ~3.3:1 (bold text OK) |

### 4. Smooth transitions without load flash

Scope transitions to a `.theme-ready` class, added by JS after initial render:

```css
html.theme-ready, html.theme-ready *,
html.theme-ready *::before, html.theme-ready *::after {
    transition: background-color 0.3s, color 0.3s, border-color 0.3s;
}
```

### 5. rgba() badge backgrounds — no changes needed

~15 hardcoded `rgba()` values at 0.15 alpha (badge backgrounds, icon backgrounds, podcast gradient) produce light pastel tints on white — standard light-mode badge design. Leave unchanged.

## Key Gotchas

- **localStorage key coupling** — The key `ai-digest-theme` must be identical in the `<head>` FOUC script and `toggleTheme()`. If one changes, both must change.
- **No `[data-theme="dark"]` block** — `:root` already serves as the dark theme. Duplicating it creates a maintenance burden.
- **Wildcard transition scope** — `html.theme-ready *` is intentional. Scoped transitions miss pseudo-elements and deeply nested components. Performance cost is negligible for a user-triggered toggle.
- **rgba() opacity** — Don't convert badge backgrounds from `rgba()` to CSS variables. The 0.15 alpha produces correct visual weight on both themes automatically.

## Prevention / Best Practices

- **Always use CSS custom properties for colors** — hardcoded hex values won't respond to theme changes.
- **Test new accent colors with a contrast checker** against both theme backgrounds before committing.
- **Keep the FOUC script minimal** — no DOM manipulation beyond setting `data-theme`. It blocks rendering.
- **Default to OS preference** — `prefers-color-scheme` respects user system settings; only override with explicit localStorage choice.

## References

- Plan: `docs/plans/2026-02-19-feat-light-dark-mode-plan.md`
- PR: https://github.com/Sven1603/ai-venture-digest/pull/6
