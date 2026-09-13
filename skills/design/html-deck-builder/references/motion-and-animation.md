# Motion and Animation

Optional motion patterns for decks that need movement: a rolling ticker, a scrolling tip bar, animated SVG diagrams, and an animated hero background. Every pattern ships with a `prefers-reduced-motion` fallback. Motion is a garnish, not a requirement. Use it when it earns its place (a long list you want to pace, a diagram that shows flow) and skip it otherwise.

All patterns assume the design tokens from `design-tokens.md` are loaded. Colors reference `--primary` and `--primary-light` so they rebrand with the rest of the deck.

## Principle: always pair motion with a reduced-motion fallback

Any animation you add must degrade gracefully for users who set `prefers-reduced-motion: reduce`. Wrap the moving pieces so they hold still, and make sure the content is still fully readable when they do. Every pattern below includes its fallback. Do not ship motion without one.

---

## 1. Vertical auto-scroll ticker

A rolling window that scrolls a list upward through a fixed viewport, showing a few items at a time. Use it for a long list you want to pace for the audience rather than dumping on one slide (a capability roundup, a timeline, a set of highlights). The speaker reads items as they roll by.

How it works: the track holds two copies of the list back to back and translates up by 50%, so the loop is seamless. Fade masks soften the top and bottom edges. An initial `animation-delay` holds the first item still long enough to read before the scroll starts. Hovering pauses it.

### HTML

```html
<div class="ticker-wrap">
  <div class="ticker-viewport">
    <div class="ticker-track">
      <!-- real items -->
      <div class="ticker-item"><div class="t-num">01</div><div class="t-body"><strong>First item</strong><span>Supporting line</span></div></div>
      <!-- ... more items ... -->
      <!-- duplicate the full set again for a seamless loop -->
      <div class="ticker-item" aria-hidden="true"><div class="t-num">01</div><div class="t-body"><strong>First item</strong><span>Supporting line</span></div></div>
      <!-- ... same items repeated ... -->
    </div>
  </div>
</div>
```

### CSS

```css
.ticker-wrap { width: 100%; max-width: 820px; }

.ticker-viewport {
  height: 60vh;
  overflow: hidden;
  position: relative;
  -webkit-mask-image: linear-gradient(to bottom, transparent 0%, #000 16%, #000 84%, transparent 100%);
  mask-image: linear-gradient(to bottom, transparent 0%, #000 16%, #000 84%, transparent 100%);
}

.ticker-track {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  animation: tickerRoll 64s linear 3s infinite; /* 3s = initial hold so item 1 is readable */
}

.ticker-viewport:hover .ticker-track { animation-play-state: paused; }

@keyframes tickerRoll {
  from { transform: translateY(0); }
  to { transform: translateY(-50%); } /* -50% because the list is duplicated */
}

.ticker-item {
  display: flex;
  gap: 1.1rem;
  align-items: flex-start;
  background: var(--off-white);
  border: 1px solid var(--border);
  border-left: 4px solid var(--primary);
  border-radius: var(--radius);
  padding: 16px 24px;
}
```

### Reduced-motion fallback

Stop the scroll and let the full list flow naturally (viewport height auto, masks off) so every item is visible and static.

```css
@media (prefers-reduced-motion: reduce) {
  .ticker-track { animation: none; }
  .ticker-viewport {
    height: auto;
    -webkit-mask-image: none;
    mask-image: none;
  }
}
```

### Notes

- Duplicate the item set exactly, and keep the keyframe end at `-50%`. If the copies do not match, the loop jumps.
- Tune speed with the duration (`64s`) and the readable-start hold with the delay (`3s`). Longer list means longer duration.
- Mark the duplicate copy `aria-hidden="true"` so screen readers do not read every item twice.

---

## 2. Horizontal marquee bar

A slim fixed bar along the bottom that scrolls one line of text right to left, so a longer tip reads fully even in a narrow strip. Good for rotating "did you know" tips or contextual notes that should not take slide space.

How it works: a JavaScript `requestAnimationFrame` loop moves the text at a fixed pixels-per-second speed from just off the right edge to fully past the left, then advances to the next tip after a pause. Fixed speed (not fixed duration) keeps long and short tips reading at the same comfortable pace.

### HTML

```html
<div class="tips-bar" id="tipsBar">
  <span class="tips-label">Did you know?</span>
  <div class="tips-viewport"><span class="tips-text" id="tipsText"></span></div>
</div>
```

### CSS

```css
.tips-bar {
  position: fixed;
  bottom: 18px;
  left: 50%;
  transform: translateX(-50%);
  width: min(560px, calc(100vw - 340px)); /* stays clear of bottom-left counter and bottom-right nav */
  background: var(--primary-light);
  border: 1px solid var(--border-accent);
  border-radius: 20px;
  padding: 5px 14px;
  z-index: 700; /* below nav chrome (z-index 900+) */
  display: flex;
  align-items: center;
  gap: 9px;
  box-shadow: var(--shadow);
  overflow: hidden;
}

.tips-bar .tips-label {
  flex-shrink: 0;
  font-size: 0.66rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--primary);
  background: var(--white);
  border: 1px solid var(--border-accent);
  border-radius: 20px;
  padding: 2px 9px;
}

.tips-bar .tips-viewport { flex: 1; overflow: hidden; position: relative; height: 1.4rem; }

.tips-bar .tips-text {
  position: absolute;
  left: 0; top: 0;
  font-size: 0.8rem;
  color: var(--text);
  line-height: 1.4;
  white-space: nowrap;
  will-change: transform;
}

.tips-bar.hidden { display: none; }
```

### JavaScript

```javascript
var tips = [
  'First tip text. Full sentences are fine; the bar scrolls the whole thing.',
  'Second tip text.'
];
var tipsText = document.getElementById('tipsText');
var tipsViewport = tipsText ? tipsText.parentElement : null;
var tipIdx = 0;
var tipRAF = null;
var SPEED = 55;        // pixels per second (slow, readable)
var END_PAUSE = 1400;  // ms pause after a tip scrolls off before the next

function runMarquee() {
  if (!tipsText || !tipsViewport) return;
  tipsText.innerHTML = tips[tipIdx];
  var vpWidth = tipsViewport.offsetWidth;
  var textWidth = tipsText.scrollWidth;
  var startX = vpWidth;      // begin just off the right edge
  var endX = -textWidth;     // end fully past the left edge
  var distance = startX - endX;
  var duration = (distance / SPEED) * 1000;
  var startTime = null;
  function step(ts) {
    if (startTime === null) startTime = ts;
    var frac = Math.min((ts - startTime) / duration, 1);
    tipsText.style.transform = 'translateX(' + (startX - distance * frac) + 'px)';
    if (frac < 1) {
      tipRAF = requestAnimationFrame(step);
    } else {
      tipIdx = (tipIdx + 1) % tips.length;
      setTimeout(runMarquee, END_PAUSE);
    }
  }
  tipRAF = requestAnimationFrame(step);
}
```

### Per-slide show and hide

Some slides should not show the bar (title, agenda, or a slide whose own content sits at the bottom, like QR codes or a source link). Drive visibility from `showSlide()` using a marker class plus checks, rather than hardcoding slide indexes:

```javascript
// inside showSlide(index):
if (tipsBar) {
  var slideEl = slides[index];
  var hideTips = !slideEl
    || slideEl.querySelector('.source')          // slide has a bottom-center source link
    || slideEl.classList.contains('no-tips')     // opt-out marker on the slide
    || index < 3;                                // intro slides
  if (hideTips) { tipsBar.classList.add('hidden'); }
  else { tipsBar.classList.remove('hidden'); }
}
```

Add `class="slide no-tips"` to any slide that should suppress the bar. This survives slide reordering, unlike an index list.

### Reduced-motion fallback

Skip the scroll. Rotate through the tips statically on a timer, letting the text wrap normally.

```javascript
var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (reduceMotion) {
  var staticIdx = 0;
  function showStatic() {
    if (!tipsText) return;
    tipsText.style.transform = 'none';
    tipsText.style.whiteSpace = 'normal';
    tipsText.innerHTML = tips[staticIdx];
    staticIdx = (staticIdx + 1) % tips.length;
  }
  showStatic();
  setInterval(showStatic, 8000);
} else {
  runMarquee();
}
```

---

## 3. Animated SVG diagram (traveling dots)

An inline SVG hub-and-spoke (or any node graph) with dots that travel along the connectors, showing direction and flow. Use it for architecture diagrams where the movement conveys something (requests going out and coming back, data flowing between nodes). It builds on the static SVG tree in `component-library.md`; the only addition is `animateMotion` on small circles.

### HTML pattern

```html
<div class="outpost-stage">
  <svg viewBox="0 0 900 520" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Hub connected to four outposts">
    <!-- spokes -->
    <path class="op-spoke" d="M450,260 L210,120"/>
    <!-- ... more spokes ... -->

    <!-- traveling dots: reuse the SAME path 'd' as the spoke they ride -->
    <circle class="op-dot" r="5" fill="#7c3aed">
      <animateMotion dur="2.6s" begin="0s" repeatCount="indefinite" path="M450,260 L210,120"/>
    </circle>
    <!-- a return dot: same path, reversed via keyPoints/keyTimes or an offset begin, in a second color -->

    <!-- nodes drawn on top -->
    <circle class="op-hub" cx="450" cy="260" r="46"/>
    <text class="op-hub-text" x="450" y="264" text-anchor="middle">Hub</text>
  </svg>
</div>
```

### CSS

```css
.outpost-stage { width: 100%; max-width: 900px; flex: 1; display: flex; align-items: center; justify-content: center; }
.outpost-stage svg { width: 100%; height: auto; max-height: 62vh; }

.op-spoke { stroke: #d9cceb; stroke-width: 2; fill: none; }
.op-hub   { fill: var(--white); stroke: var(--primary); stroke-width: 2.5; }
.op-hub-text { fill: var(--primary); font-weight: var(--fw-bold); font-family: var(--font); }
```

### Notes

- Each dot's `animateMotion path` must match the `d` of the spoke it rides. Copy the coordinates exactly.
- Use two dot colors to show two directions (for example purple outbound, blue return). Stagger them with different `begin` offsets so they do not overlap.
- `animateMotion` is declarative SMIL; it needs no JavaScript and loops on its own with `repeatCount="indefinite"`.
- Draw nodes after the dots in source order so nodes render on top.

### Reduced-motion fallback

Hide the dots; the static diagram still communicates the structure.

```css
@media (prefers-reduced-motion: reduce) {
  .op-dot { display: none; }
}
```

---

## 4. Animated hero background (orbit)

A slow, low-opacity animated SVG sitting behind the hero title: concentric rings with dots orbiting a pulsing core. Purely ceremonial motion for a title or section divider. Keep it faint so it never competes with the title.

### HTML (inside a hero slide, before the title content)

```html
<svg class="hero-orbit" viewBox="0 0 620 620" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle class="ring" cx="310" cy="310" r="150"/>
  <g class="spin">
    <circle class="surface" cx="310" cy="160" r="9"/>
  </g>
  <g class="spin-rev">
    <circle class="surface" cx="310" cy="530" r="8"/>
  </g>
  <circle class="core" cx="310" cy="310" r="8"/>
</svg>
```

### CSS

```css
.hero-orbit {
  position: absolute;
  top: 50%; left: 50%;
  width: 620px; height: 620px;
  transform: translate(-50%, -50%);
  z-index: 1;
  pointer-events: none;
  opacity: 0.5;
}
.hero-orbit .ring { fill: none; stroke: var(--primary); opacity: 0.12; }
.hero-orbit .surface { fill: var(--primary); opacity: 0.55; }
.hero-orbit .spin { transform-origin: 310px 310px; animation: heroSpin 26s linear infinite; }
.hero-orbit .spin-rev { transform-origin: 310px 310px; animation: heroSpin 34s linear infinite reverse; }
.hero-orbit .core { fill: var(--primary); animation: heroPulse 3.2s ease-in-out infinite; }

@keyframes heroSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes heroPulse { 0%, 100% { r: 8; opacity: 0.9; } 50% { r: 11; opacity: 0.5; } }
```

### Reduced-motion fallback

```css
@media (prefers-reduced-motion: reduce) {
  .hero-orbit .spin, .hero-orbit .spin-rev { animation: none; }
  .hero-orbit .core { animation: none; }
}
```

### Watch the cascade

The title content must sit above the orbit and stay in normal flow. See the cascade gotcha in `content-rules.md`: a broad `.slide > *` position rule can accidentally pull an absolutely-positioned `.hero-orbit` into flow and push the title down. Exclude it with `:not(.hero-orbit)`.

---

## 5. Faded full-bleed background image on a content slide

A base64 image covering the whole slide at very low opacity, with content layered above it. Use sparingly, on a slide whose topic the image reinforces (a product screenshot behind an "Agents" slide, for example). The base template reserves background images for hero slides only; this extends that to content slides at low enough opacity that text stays readable.

### HTML (first child of the slide)

```html
<div class="slide">
  <img class="slide-bg" src="data:image/png;base64,..." alt="">
  <div class="slide-heading"> ... </div>
  <!-- rest of the slide -->
</div>
```

### CSS

```css
.slide-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.06;          /* keep 0.04 to 0.08; higher competes with text */
  pointer-events: none;
  z-index: 0;
}

/* content sits above the background, but do NOT force positioned decorations into flow */
.slide > *:not(.slide-bg):not(.hero-orbit):not(.source):not(.title-footer) {
  position: relative;
  z-index: 1;
}
```

### Notes

- Keep opacity in the 0.04 to 0.08 range. Anything higher and text contrast suffers.
- Mark the image `alt=""` (decorative) so screen readers skip it.
- The `:not(...)` exclusions on the z-index rule matter. Without them the rule forces every absolutely-positioned child (orbit, source link, footer) into normal flow and breaks the layout. See the cascade gotcha in `content-rules.md`.
- Compress the image before embedding; a full-bleed raster at low opacity does not need full resolution. See file-size guidance in `content-rules.md`.
