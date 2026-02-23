---
title: "SVG Header Image with Blinking Eyes Animation: CSS-in-SVG and Hero Layout"
date: 2026-02-23
category: ui-bugs
module: index.html, assets/header-img.svg
tags:
  - svg-animation
  - css-in-svg
  - hero-layout
  - responsive-image
  - object-fit
  - wave-divider
  - sub-pixel-rendering
symptoms:
  - "CSS animations inside SVG do not play when SVG is loaded via background-image"
  - "Hero image cropped — full illustration height not visible"
  - "Content overlaps illustration on mobile (hero too short at narrow viewports)"
  - "Thin hairlines visible between wave divider SVGs and adjacent sections"
  - "Junk HTML tags at end of file from accumulated edits"
severity: medium
pr: 9
related:
  - docs/solutions/ui-bugs/light-dark-mode-theming.md
  - docs/solutions/ui-bugs/intersection-observer-scroll-spy.md
---

## Problem Statement

The hero section used a PNG background image (`background: url('assets/header-img.png')`) of a coffee shop robot scene. The goals were to: (1) swap to an SVG version for quality and scalability, (2) add blinking eye animations to the characters in the illustration, and (3) maintain responsive layout across desktop and mobile.

The SVG file is ~300KB with 729 unlabeled `<path>` elements — no semantic IDs or group structure to identify which paths represent eyes.

## Root Cause

### 1. CSS animations don't work inside SVGs loaded via `background-image`

The CSS `background-image: url('file.svg')` property renders the SVG as a static raster — the browser does not execute `<style>` blocks or animations embedded in the SVG. This is a security/performance restriction in all major browsers. Only `<img>` tags (and `<object>`/`<iframe>`) allow internal SVG animations to play.

### 2. No semantic structure in the SVG

The illustration SVG contained 729 flat `<path>` elements with no `id`, `class`, or `<g>` grouping. Eye elements had to be identified by computing bounding boxes of all paths and matching them against visually identified eye locations.

### 3. Flow vs. fixed-height hero

The original `background-image` approach used a fixed `min-height` on the hero, cropping the illustration. Showing the full image height required switching to a flow-based layout where the `<img>` element defines the section height.

### 4. Mobile breakpoint mismatch

On narrow viewports (~390px), the flow-based hero became too short (~260px) because the SVG's aspect ratio compresses vertically. Required a different strategy: fixed minimum height with `object-fit: cover`.

### 5. Sub-pixel rendering gaps at wave dividers

SVG wave dividers between sections leave hairline gaps at certain zoom levels and device pixel ratios due to anti-aliasing and sub-pixel rounding between adjacent colored regions.

## Solution

### Step 1: Identify eye elements via bounding box analysis

Used a Python script to parse all `<path>` elements, compute their bounding boxes via the `d` attribute coordinates, and match paths falling within known eye regions of the illustration. Identified 5 character eye groups:

| Character | Animation Delay | Paths |
|-----------|----------------|-------|
| Left robot | 0s | 2 paths |
| Right robot | 0.3s | 2 paths |
| Yellow mug | 1s | 2 paths |
| Mascot bear | 1.2s | 2 paths |
| Cloud creature | 3.5s | 2 paths |

### Step 2: Wrap eye paths in animated groups inside the SVG

Added a `<style>` block inside the SVG with a double-blink keyframe animation, then wrapped each pair of eye paths in a `<g>` element with appropriate `transform-origin` and `animation-delay`:

```xml
<!-- Inside the SVG -->
<style>
  .blink-eyes {
    animation: blink 5s ease-in-out infinite;
  }
  @keyframes blink {
    0%, 100% { transform: scaleY(1); }
    3%       { transform: scaleY(0.05); }
    6%       { transform: scaleY(1); }
    10%      { transform: scaleY(0.05); }
    13%      { transform: scaleY(1); }
  }
  .blink-left-robot  { transform-origin: 313px 495px; animation-delay: 0s; }
  .blink-right-robot { transform-origin: 513px 432px; animation-delay: 0.3s; }
  .blink-mug         { transform-origin: 157px 483px; animation-delay: 1s; }
  .blink-mascot      { transform-origin: 670px 475px; animation-delay: 1.2s; }
  .blink-cloud       { transform-origin: 520px 175px; animation-delay: 3.5s; }
</style>
```

### Step 3: Switch hero from background-image to `<img>` tag

```html
<!-- Before -->
<section class="hero" style="background: url('assets/header-img.png') center/cover;">

<!-- After -->
<section class="hero">
  <img src="assets/header-img.svg" alt="" class="hero-bg" aria-hidden="true">
  <div class="hero-content">...</div>
</section>
```

### Step 4: Flow-based desktop layout with content in blue sky area

```css
.hero {
  position: relative;
  overflow: hidden;
  text-align: center;
}
.hero-bg {
  display: block;
  width: 100%;
  height: auto;
}
.hero-content {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 55%;  /* constrain to the blue sky portion */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1;
  padding: 0 24px;
}
```

The `height: 55%` constrains the text overlay to the upper blue sky portion of the illustration, keeping it clear of the foreground characters.

### Step 5: Mobile responsive fallback

```css
@media (max-width: 768px) {
  .hero { min-height: 420px; }
  .hero-bg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 30%;
  }
  .hero-content {
    height: auto;
    padding: 32px 16px;
    justify-content: flex-start;
  }
}
```

On mobile, the image switches from flow element to absolute-positioned cover, with `object-position: center 30%` to show the sky and upper portion of the scene.

### Wave divider gap (deferred)

Tried multiple approaches to eliminate sub-pixel hairlines between wave SVGs and sections:
- `scaleY(1.05)` on the SVG — partial improvement
- Aggressive negative margins (`margin: -6px 0`) — reduced but not eliminated
- `padding-bottom` percentage — no effect
- z-index layering — no effect

Current mitigation: `height: 60px; margin: -6px 0` on `.wave-divider`. A TODO comment marks this for future investigation. The hairlines are only visible at certain zoom levels and device pixel ratios.

## Key Technical Decisions

1. **`<img>` tag over `<object>` or inline SVG**: `<img>` is the simplest approach that allows CSS animations inside the SVG while keeping the SVG file separate. Inline SVG would bloat the HTML (~300KB). `<object>` adds iframe-like complexity.

2. **Staggered animation delays**: Each character blinks at a different offset (0s to 3.5s) creating a natural, non-synchronized feel. The double-blink keyframe (blink at 3% and 10%) mimics real eye blink patterns.

3. **`scaleY(0.05)` not `scaleY(0)`**: Using 0.05 instead of 0 prevents the eyes from completely disappearing (which looks jarring) and gives a more natural squint effect.

4. **`height: 55%` content area**: Rather than pixel-based positioning, percentage-based height adapts to any viewport width while keeping text in the sky region.

5. **Separate desktop/mobile strategies**: Desktop uses the natural image flow for full-height display; mobile uses `object-fit: cover` with a minimum height to prevent an unusably short hero.

## Known Issues

- **Wave divider hairlines**: Thin lines (1px or sub-pixel) visible between wave SVG dividers and adjacent sections at some zoom levels and on some devices. Marked with TODO in `index.html`. This is a well-known browser rendering issue with adjacent SVG/CSS regions and has no universal CSS-only fix.

## Files Changed

| File | Change |
|------|--------|
| `assets/header-img.svg` | Added `<style>` block with blink animation, wrapped 10 eye paths in 5 `<g class="blink-eyes">` groups |
| `index.html` | Hero: `background-image` → `<img>` tag, flow layout, content overlay at 55% height, mobile responsive fallback, wave divider margin fix, removed junk HTML at EOF |

## Prevention

- **Always use `<img>` (not `background-image`) for SVGs that contain animations or interactivity.** CSS `background-image` renders SVGs as static bitmaps.
- **When working with large unstructured SVGs**, use scripted bounding-box analysis rather than manual path identification — the SVG had 729 paths with no labels.
- **Test mobile viewports early** when changing hero layout strategy. Flow-based image sizing behaves very differently at narrow widths vs. desktop.
- **Sub-pixel gaps between adjacent sections** are a browser rendering limitation, not a code bug. Negative margins and overlapping elements are mitigation, not a fix.
