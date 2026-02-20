---
title: "IntersectionObserver Scroll Spy: Preventing Race Conditions and Resource Leaks"
date: 2026-02-20
category: ui-bugs
module: index.html
tags:
  - scroll-spy
  - IntersectionObserver
  - resource-cleanup
  - race-conditions
  - animation-timing
  - resize-handlers
symptoms:
  - "Pill/indicator bounces through intermediate sections on click-to-scroll"
  - "Duplicate observer callbacks after re-render"
  - "Resize causes layout thrashing and stutter"
  - "Stale timeout re-enables observer during smooth scroll"
  - "Wrong section activates when multiple sections enter viewport"
severity: medium
related:
  - docs/solutions/ui-bugs/light-dark-mode-theming.md
---

## Problem Statement

Building an IntersectionObserver-based scroll spy with an animated sliding indicator (pill, underline, tab marker) in a single-page app is deceptively fragile. The core challenge: a single `buildTOC()` (or equivalent) function is called every time the view re-renders, the observer and event listeners accumulate across calls, and the animated indicator must remain correct across three competing sources of change — scroll, click, and window resize — without flickering, bouncing, or getting out of sync.

## Symptoms

- Pill / indicator bounces back through intermediate sections when the user clicks a TOC item (observer fires during smooth scroll)
- Clicking the same or a nearby item rapidly causes the indicator to freeze at a wrong position (stale `setTimeout` re-enables the observer too early or too late)
- After several `renderAll()` calls, the observer callback fires multiple times per scroll event (duplicate observers from prior builds still attached)
- Window resize stutters or triggers continuous layout thrashing (non-debounced resize handler reads `offsetLeft`/`offsetWidth` synchronously on every pixel change)
- At page load the indicator animates from position 0 to the first item (animation fires when it should not)
- When multiple sections enter the viewport simultaneously, the wrong section becomes active (entry order in the IntersectionObserver callback is not guaranteed by spec)

## Root Cause

### 1. Observer / listener leak when rebuild function is called multiple times

`new IntersectionObserver(...)` creates a fresh observer each call. If the previous observer is not disconnected, both remain active and both fire their callbacks on every scroll event. Similarly, `window.addEventListener('resize', handler)` accumulates listeners.

### 2. Stale `setTimeout` not cleared on rapid sequential clicks

The pattern `setTimeout(() => { suppress = false }, 800)` starts a new timer on every click without cancelling the previous one. A second click 300 ms after the first sets a new 800 ms timer; the first timer fires at T+800 and re-enables the observer while the second scroll is still in flight.

### 3. Always-true `animate` check masking logic intent

The guard `if (!animate)` inside a function with signature `movePill(link, animate)` must explicitly handle both `false` and `undefined`. Relying on truthiness alone means passing `animate = undefined` (the common accidental case) behaves identically to `animate = true`, and the no-animation initial-placement path is silently skipped.

### 4. Non-debounced resize handler causing layout thrashing

Reading layout properties (`offsetLeft`, `offsetWidth`, `offsetHeight`) inside a raw `resize` listener forces synchronous layout on every event, which fires tens of times per second during a drag-resize. On slow devices this causes visible jank.

### 5. Observer callback entry order not guaranteed by spec

The IntersectionObserver callback receives a batch of entries representing all threshold crossings since the last callback. The spec does not guarantee their order. Picking `entries[entries.length - 1]` or the last `isIntersecting: true` entry to determine the "topmost visible" section produces inconsistent results; the correct approach is to compare geometry.

## Solution

### Teardown pattern for IntersectionObserver + event listeners

Store the observer and resize handler in variables that survive re-renders. At the top of every rebuild, disconnect and remove them before creating new ones.

```js
let _observer = null;
let _resizeHandler = null;

function buildNav() {
    // Tear down previous instance before rebuilding
    if (_observer) { _observer.disconnect(); _observer = null; }
    if (_resizeHandler) { window.removeEventListener('resize', _resizeHandler); _resizeHandler = null; }

    // ... build DOM, create new observer ...

    _observer = new IntersectionObserver(onIntersect, options);
    sections.forEach(el => _observer.observe(el));

    _resizeHandler = onResize;
    window.addEventListener('resize', _resizeHandler);
}
```

### `clearTimeout` pattern for click-to-scroll suppression

Always cancel the previous timer before starting a new one, and capture the timeout ID in a variable that persists across click events.

```js
let suppress = false;
let suppressId = null;

link.addEventListener('click', () => {
    setActive(link);
    clearTimeout(suppressId);           // cancel any pending re-enable
    suppress = true;
    target.scrollIntoView({ behavior: 'smooth' });
    suppressId = setTimeout(() => { suppress = false; }, 800);
});
```

### `requestAnimationFrame` debounce for resize handlers

Cancel the pending animation frame before scheduling a new one. This coalesces all resize events in a single animation frame into one layout read, eliminating thrashing.

```js
let rafId = 0;

function onResize() {
    cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
        // safe to read layout here — exactly once per frame
        repositionIndicator(activeEl, false);
    });
}
```

### Topmost-entry selection in observer callbacks

Do not rely on entry order. Instead, iterate all intersecting entries and keep the one whose top edge is closest to the top of the viewport.

```js
function onIntersect(entries) {
    if (suppress) return;
    let topmost = null;
    let topmostY = Infinity;
    entries.forEach(entry => {
        if (entry.isIntersecting && entry.boundingClientRect.top < topmostY) {
            topmostY = entry.boundingClientRect.top;
            topmost = entry.target;
        }
    });
    if (topmost) setActive(linkFor(topmost));
}
```

### Default parameter pattern for optional animation control

Use an explicit default parameter instead of a truthiness check to make the no-animation path unambiguous.

```js
// Caller passes false explicitly to suppress animation;
// omitting the argument (or passing true) enables animation.
function moveIndicator(el, animate = true) {
    if (!animate) {
        indicator.style.transition = 'none';
    }
    indicator.style.width = el.offsetWidth + 'px';
    indicator.style.transform = 'translateX(' + el.offsetLeft + 'px)';
    if (!animate) {
        indicator.offsetHeight;      // force reflow to flush the no-transition state
        indicator.style.transition = '';
    }
}
```

## Key Takeaway

An animated scroll spy built on IntersectionObserver has three independent cleanup obligations — disconnecting the observer, removing the resize listener, and cancelling the suppression timer — and each must be handled explicitly every time the component is rebuilt. Missing any one of them produces a different class of bug (duplicate callbacks, stale suppress state, or layout thrashing), all of which manifest as animation glitches that are difficult to reproduce in isolation. Treating the rebuild function as a full teardown-then-reconstruct operation, and storing all teardown handles in outer-scope variables, is the reliable pattern.
