# Design Tokens

Complete CSS custom property system for HTML presentations. All values are tunable; override `--primary` to rebrand the entire deck.

## Color Palette

```css
:root {
  /* Brand colors */
  --primary: #6B2FA0;
  --primary-light: #F5F0FA;
  --primary-gradient: linear-gradient(135deg, #6B2FA0, #9B59B6);

  /* Neutrals */
  --dark: #232F3E;
  --white: #ffffff;
  --off-white: #fafafa;
  --text: #1a1a2e;
  --text-muted: #555;
  --border: #eee;

  /* Derived from primary */
  --border-accent: rgba(107, 47, 160, 0.2);
  --shadow: 0 2px 12px rgba(107, 47, 160, 0.08);
  --shadow-hover: 0 4px 20px rgba(107, 47, 160, 0.15);
}

```

## Rebranding

To use a different primary color, override these four derived values:

```css
/* Example: blue brand (#1a73e8) */
:root {
  --primary: #1a73e8;
  --primary-light: #f0f6ff;
  --primary-gradient: linear-gradient(135deg, #1a73e8, #4da3ff);
  --border-accent: rgba(26, 115, 232, 0.2);
  --shadow: 0 2px 12px rgba(26, 115, 232, 0.08);
}

```

## Badge Colors

Semantic colors for status badges in data tables:

```css
:root {
  --badge-green: #e8f5e9;
  --badge-green-text: #2e7d32;
  --badge-blue: #e3f2fd;
  --badge-blue-text: #1565c0;
  --badge-orange: #fff3e0;
  --badge-orange-text: #e65100;
  --badge-purple: var(--primary-light);
  --badge-purple-text: var(--primary);
}

```

## Typography

```css
:root {
  --font: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;

  /* Scale */
  --fs-title: 1.8rem;    /* Slide heading (h2) */
  --fs-section: 1.1rem;  /* Section heading (h3) */
  --fs-body: 0.9rem;     /* Body text */
  --fs-small: 0.8rem;    /* Captions, source links */
  --fs-mono: 0.85rem;    /* Code, field names */

  /* Weights */
  --fw-bold: 700;
  --fw-semi: 600;
  --fw-normal: 400;

  /* Line heights */
  --lh-tight: 1.3;
  --lh-normal: 1.5;
  --lh-relaxed: 1.7;
}

```

## Spacing

```css
:root {
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  --space-3xl: 64px;

  /* Content constraints */
  --content-width: 850px;
  --slide-padding-top: 64px;
  --slide-padding-x: 80px;
  --slide-padding-bottom: 60px;
}

```

## Borders and Radius

```css
:root {
  --radius: 14px;
  --radius-sm: 8px;
  --radius-xs: 4px;
  --radius-round: 50%;

  --border-width: 2px;
  --border-thick: 4px;
}

```

## Shadows

```css
:root {
  --shadow: 0 2px 12px rgba(107, 47, 160, 0.08);
  --shadow-hover: 0 4px 20px rgba(107, 47, 160, 0.15);
  --shadow-card: 0 1px 8px rgba(0, 0, 0, 0.06);
  --shadow-notes: -4px 0 20px rgba(0, 0, 0, 0.3);
}

```

## Transitions

```css
:root {
  --transition-fast: 0.2s ease;
  --transition-normal: 0.3s ease;
  --transition-slide: 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

```

## Z-Index Scale

```css
:root {
  --z-slide: 1;
  --z-source: 5;
  --z-chrome: 100;        /* Nav buttons, progress bar */
  --z-notes: 1000;        /* Speaker notes panel */
  --z-notes-toggle: 1001; /* Notes toggle button */
}

```

## Responsive Breakpoints

The deck is designed for 16:9 presentation on desktop. For smaller viewports:

```css
@media (max-width: 900px) {
  :root {
    --content-width: 95%;
    --slide-padding-x: 32px;
    --fs-title: 1.4rem;
    --fs-section: 1rem;
  }
}

```
