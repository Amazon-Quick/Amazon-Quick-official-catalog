---
description: "Content principles for HTML presentation slides, including the 5/5/5 rule, one-message-per-slide guidance, and standard slide layouts."
last_updated: 2026-09-13
origin: original
---

# Content Rules

Principles for slide content that prevent the common failure modes of AI-generated presentations.

## The 5/5/5 Rule

Every content slide must satisfy all three constraints:

1. **Max 5 words per line** in any card, bullet, or heading
2. **Max 5 items** in any list, grid, or sequence
3. **Max 5 visual elements** on a single slide (components, images, cards all count)

If content exceeds these limits, either:

- Split across multiple slides (preferred for distinct ideas)
- Move overflow into speaker notes (preferred for supporting detail)

## One Message Per Slide

Each slide communicates exactly one idea. The audience should absorb the slide's point in under 5 seconds of looking at it. If you need a sentence to explain what the slide is about, it has too much content or competing messages.

## Slide Layouts

### Hero Slides

Used for: title, demo, Q&A, section dividers.

```
- Vertically and horizontally centered
- Large text only (title + optional subtitle)
- Optional background image at low opacity (30-40%)
- No components or data; purely ceremonial

```

### Content Slides

Used for: everything substantive.

```
- Heading (h2) starts 64px from top (consistent across all slides)
- Content flows top-to-bottom within max-width container
- If content exceeds viewport height, slide scrolls (overflow-y: auto)
- Source link anchored at bottom-center (absolute positioned)
- Padding: 64px top, 80px sides, 60px bottom

```

## Speaker Notes

The speaker notes panel is the expansion layer. Detail lives there, not on slides.

### What goes in notes:

- Full talking points (what you will say out loud)
- Source citations with working URLs
- Technical details that support the slide's single message
- Transition phrases to the next slide
- Numbers, statistics, verbatim quotes

### What stays on slides:

- The headline takeaway
- Visual structure (diagrams, tables, cards)
- Key terms (not full explanations)
- Maximum 50 words of visible text per slide

### Format:

```
data-notes="Talking point one. Talking point two. Source: https://..."

```

Keep notes as plain sentences. No markdown formatting (it renders as raw text in the panel).

## Source Links

Every content slide has a source link centered at the bottom. This establishes credibility and gives the audience a reference.

```html
<div class="source">
  <a href="https://docs.aws.amazon.com/..." target="_blank">docs.aws.amazon.com/...</a>
</div>

```

Rules:

- Must be a working hyperlink (not plain text)
- Display URL should be shortened (drop `https://`, truncate path)
- Opens in new tab (`target="_blank"`)
- Position: absolute bottom-center, 20px from bottom edge
- Font size: var(--fs-small), color: var(--text-muted)

## Visual Hierarchy

Use size, color, and spacing to create clear reading order:

1. **Slide title** (h2): largest, darkest, top position
2. **Section headings** (h3): brand color, medium weight
3. **Body content**: smaller, neutral color
4. **Captions/notes**: smallest, muted color

Never compete with the title. Nothing on a content slide should be visually louder than the h2.

## Anti-Patterns to Avoid

### Text failures

- Wall of text (paragraphs on slides)
- Bullet-point exhaustion (more than 5 bullets)
- Complete sentences where a phrase would suffice
- Repeating what the speaker will say verbatim

### Design failures

- Plain white background with no visual interest
- Inconsistent card/border styles between slides
- Multiple competing focal points
- Emojis used as icons (use inline SVGs instead)
- Unstyled default HTML tables

### Structural failures

- More than 12 slides for a 30-minute talk
- Less than 6 slides (each one overloaded)
- No speaker notes (speaker will ad-lib and lose structure)
- Missing navigation chrome (audience can't tell progress)

### Writing failures

- AI-sounding phrases ("It's important to note that...")
- Em dashes (use periods or semicolons)
- Hedging language ("This can potentially help...")
- Buzzword density without concrete meaning

## Image Guidelines

### Background images

- Opacity: 30-40% (must not compete with foreground text)
- Position: centered, cover
- Only on hero slides; content slides stay clean

### Inline images

- Max width: 60% of content area for screenshots
- Max width: 100% for diagrams that need full bleed
- Always add alt text
- Prefer SVG for diagrams (scalable, smaller file size)

### QR codes

- Minimum 120x120px rendered size (must be scannable)
- White padding around the code
- Always pair with a text label (what it links to)

## File Size Guidelines

Single-file HTML presentations should stay under 2MB total. If embedded images push past this:

- Compress PNGs (use run_python with Pillow, quality reduction)
- Consider linking images from a URL instead of base64 embedding
- SVG diagrams are almost always smaller than raster screenshots

## Editing Safety Protocol

Large single-file decks (with base64 images the file runs to over 1MB) are fragile to edit. Fuzzy or diff-based edits against a giant file have repeatedly stranded CSS above `<html>` and dropped the `<!DOCTYPE>` line, which silently blanks slides (the browser mis-parses the document). Follow this protocol for every edit to an existing deck.

### Edit with exact strings, not fuzzy context

- Prefer exact-string replacement: read the precise current substring, then replace it. Guard every replacement with an assertion that the anchor appears exactly once before you write.
- Never append a large CSS block by loosely targeting "the end of the style tag." Anchor on a specific, unique existing rule and insert relative to it.
- Make one logical change per write, then verify, rather than batching many blind edits.

### Run an integrity sweep after every edit

After any structural edit, verify all of the following before showing the deck. If any fails, stop and fix it before proceeding:

1. `<!DOCTYPE` count is exactly 1, and nothing appears before `<html>` except that doctype line.
2. Exactly one `<style>` and one `</style>`.
3. Exactly one `<html>`/`</html>` and one `<body>`/`</body>`.
4. Per-slide `<div>` balance: within each slide section, the count of `<div` equals the count of `</div>`. An imbalance means one slide has swallowed the slides after it (they will render blank).
5. Slide count matches the expected total, and the JS slide total matches it.
6. JavaScript brace `{ }` and paren `( )` counts are balanced.

A quick way to catch the swallowed-slide case is to split the deck on the slide delimiter and check `<div` vs `</div>` counts per section; the first section with a nonzero balance is where the break is.

### If the structure is already broken

Symptom: later slides render blank, or the whole page is unstyled white. Causes seen in practice:

- CSS stranded above `<html>` with the doctype dropped. Fix: re-prepend `<!DOCTYPE html>`, move the stray CSS back inside `<style>`.
- A slide missing its closing `</div>`s, so following slides are nested inside it. Fix: find the slide whose div balance is positive and restore its closing tags (the orphaned content is often relocated elsewhere in the file).

## CSS and JS Gotchas

These bite specifically when adding motion, backgrounds, or per-slide behavior. See `motion-and-animation.md` for the patterns these support.

### Cascade: broad descendant rules override positioned children

A rule like `.slide > *:not(.slide-bg) { position: relative; }` has higher specificity (0,2,0) than a single-class rule like `.hero-orbit { position: absolute; }` (0,1,0). It will silently force absolutely-positioned children (an animated hero background, a bottom-center source link, a title footer) into normal flow, which pushes content down or misplaces it. When you add a background-layering rule, exclude the positioned decorations explicitly:

```css
.slide > *:not(.slide-bg):not(.hero-orbit):not(.source):not(.title-footer) { position: relative; z-index: 1; }
```

Reason from specificity, not intuition: if a layout shifts after adding a broad rule, check what that rule outranks.

### JavaScript init order: define DOM refs before the first render

Call your initial `showSlide(0)` (or equivalent first render) only after every DOM reference and helper it touches is defined. If `showSlide` hides a bar or reads an element that is declared later in the script, the first render silently no-ops and the behavior only starts working after the user navigates once. Put all `getElementById` lookups and the tips/marquee setup above the initial render call.
