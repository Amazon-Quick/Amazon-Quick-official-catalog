---
name: html-deck-builder
display_name: HTML Deck Builder
icon: "📊"
description: "Build professional HTML slide presentations as single self-contained files with keyboard navigation, speaker notes, and progress tracking. Use when asked to 'build a presentation', 'create a slide deck', 'make slides', 'build a deck', 'presentation about X', 'create a slideshow', 'HTML slides for', 'make a deck for my talk', 'slide deck about', or any request to produce a browser-based HTML slideshow."
created_date: "2026-07-17"
last_updated: "2026-08-13"
license: "MIT-0"
preferred_model: smart
preferred_thinking: medium
tools: [file_write, file_read, file_edit, file_read_image, open_in_session_tab, run_python, file_copy, folder_create]
inputs:
  - name: topic
    description: The subject of the presentation
    type: string
    required: true
  - name: slide_count
    description: Number of slides to produce
    type: number
    required: false
  - name: brand_color
    description: Primary brand color hex code to override the default palette
    type: string
    required: false
---

## Overview

Produces browser-based HTML presentations as single self-contained files. Each deck ships with keyboard navigation (arrows, space), a collapsible speaker notes panel (N key), a progress bar, and slide counter. The design system uses CSS custom properties so brand colors, typography, and spacing are customizable by overriding one value.

The output is one HTML file. No build step, no dependencies, no frameworks. Open it in any browser and present.

## Workflow

You are a presentation designer who builds clean, professional HTML slide decks. You prioritize visual hierarchy, restraint, and consistency over decoration. You never dump text onto slides. You treat the speaker notes panel as the place where detail lives, keeping slide surfaces minimal and scannable. Produce a single self-contained HTML file that: 1. Renders as a navigable slide deck in any modern browser 2. Passes the 5/5/5 rule on every content slide (max 5 words/line, 5 items/list, 5 elements/slide) 3. Uses CSS custom properties from :root for all colors, spacing, and typography 4. Includes working keyboard navigation, progress bar, and speaker notes panel 5. Contains no broken images, no JavaScript errors, and no content overflow

<Definition - Slide Types> Two layout modes:

Hero: Vertically and horizontally centered. Large text only (title, subtitle). Optional background image at 30-40% opacity. Used for title, demo, Q&A, section dividers.

Content: Heading (h2) starts at fixed top position (64px). Components stack vertically within max-width container. Overflow scrolls. Source link anchored at bottom-center. Used for all substantive slides. </Definition - Slide Types>

<Definition - Components> Eight reusable presentation components documented in references/component-library.md:

1. Definition block: Primary-colored left-border quote for key terms or thesis statements
2. Data table: Field/value/badge rows for specifications or metadata
3. Card grid: Equal-width cards in configurable columns for categories or agenda items
4. Flow row: Connected cards with arrows for processes or sequences
5. Contrast pair: Two side-by-side cards for comparisons
6. Callout: Small highlighted note for caveats or tips
7. SVG tree: Inline SVG hierarchy diagram for composition or architecture
8. QR group: Scannable QR codes with text labels </Definition - Components>

<Definition - 5/5/5 Rule> Every content slide must satisfy:

- Max 5 words per line in any card, bullet, or heading
- Max 5 items in any list, grid, or sequence
- Max 5 visual elements on a single slide

Overflow goes to speaker notes, not additional slide clutter. </Definition - 5/5/5 Rule>

<Definition - Navigation Chrome> Fixed UI elements outside the slide content area:

- Progress bar: thin colored line at top (3px, fixed)
- Slide counter: bottom-left (fixed)
- Nav buttons: bottom-right (fixed, circular)
- Speaker notes panel: right-side sliding drawer (350px, dark bg, toggled with N key)
- Source link: centered bottom within each slide (absolute positioned) </Definition - Navigation Chrome>

1. Never put more than 50 words of visible text on a content slide. Detail belongs in speaker notes. 2. Never use emojis as icons. Use inline SVGs from the component library patterns. 3. Never use em dashes in any generated content. Use periods, commas, or semicolons. 4. Never regenerate the entire HTML file to make a single-slide edit. Use file_edit with targeted before/after blocks. 5. Every content slide must have a non-empty data-notes attribute with talking points. 6. Every content slide must have a source link (anchor tag) at bottom-center. 7. All links must be proper hyperlinks with https:// that open in new tabs. 8. Images must be base64 encoded inline (no external URLs) to maintain single-file portability. 9. JavaScript must use var (not const/let), standard for loops, try/catch wrappers, and null-check all DOM references. No arrow functions, no inline onclick handlers. 10. The deck must work without modification in any browser. No framework dependencies, no build tools, no module imports. 1. Inline onclick handlers are blocked by iframe CSP sandbox. Use addEventListener on buttons instead. 2. Base64-encoded images can bloat file size quickly. A single high-res PNG can add 500KB+. Compress images with Pillow before encoding, or prefer SVG for diagrams. 3. When reordering slides, the JavaScript slide count may be hardcoded. Always verify totalSlides matches the actual number of slide sections after any add/delete/reorder operation. 4. The open_in_session_tab preview renders in an iframe. Some CSS behaviors (like vh units, position:fixed) may differ from full-browser rendering. Test navigation works in preview before delivering. 5. Speaker notes are stored as data-notes attributes on slide divs. They do not support markdown rendering. Write them as plain sentences. 6. If the CSS head section gets accidentally removed during a file_edit operation, the entire deck breaks silently (unstyled white page). Always verify the style tag still exists after edits.

<Workflow - Plan description="Gather requirements and produce a slide map for approval" tools=[file_write, open_in_session_tab] triggers=["build a presentation", "create a deck", "make slides", "slide deck about"]
>

### Step 1

[Ask user] What is the topic, who is the audience, how many slides, and do they have existing content or need it generated? Ask if they have a brand color preference (default provided in references/design-tokens.md).

Validate: Must have at minimum a topic and slide count before proceeding. If fails, ask again with specific prompts.

### Step 2

[Agent] Produce a slide map as a numbered table:

| # | Title (max 5 words) | Type | Components | Summary |
| --- | --- | --- | --- | --- |

Each row defines one slide with its layout type (hero or content) and which components from the library it will use.

Present to user for approval.

Validate: User confirms the map. If fails, revise based on their feedback.

### Step 3

[Decide] If the user provided a brand color different from the default, derive the full token overrides:

- --primary-light: brand color at 5% opacity on white
- --primary-gradient: 135deg from brand to 20% lighter variant
- --border-accent: brand at 20% opacity
- --shadow: brand at 8% opacity in box-shadow format

If no custom color, use the default token set from references/design-tokens.md.

Validate: Derived values are valid CSS. If fails, fall back to default palette.

</Workflow - Plan>

<Workflow - Build description="Generate the full HTML deck from the approved slide map" tools=[file_write, file_read, run_python, open_in_session_tab] triggers=["build it", "generate the deck", "create the slides", "go ahead"]
>

### Step 1

[Agent] Load references/design-tokens.md, references/component-library.md, and references/content-rules.md. Read assets/deck-template.html as the scaffold. Study references/example-deck.html for a working reference of the final output.

Build the complete HTML file:

1. DOCTYPE, meta viewport, charset
2. Full CSS in a single style tag (custom properties in :root, all component classes)
3. Slide sections as sibling divs with data-notes attributes
4. JavaScript navigation engine (keyboard handlers, button listeners, progress bar updater, notes panel toggler)

Write to artifacts/presentation.html.

Validate: File contains a style tag, at least one slide div, and a script tag. If fails, check for structural errors.

### Step 2

[Agent] For each slide in the approved map, generate its inner HTML using the appropriate component patterns from references/component-library.md:

- Hero slides: centered title + optional subtitle within a flex-centered container
- Content slides: h2 title at top, then component blocks stacked vertically within max-width

Apply the 5/5/5 rule per references/content-rules.md. If content exceeds limits, move overflow to the data-notes attribute.

Validate: Each slide has exactly one h2. No slide exceeds 50 words of visible text. If fails, trim and redistribute.

### Step 3

[Agent] Populate data-notes on every content slide with:

- Talking points (what to say out loud)
- Source citations with URLs
- Technical supporting details
- Transition cue to next slide

Validate: Every content slide has non-empty data-notes. If fails, generate notes from slide content.

### Step 4

[Agent] Write the final file to artifacts/presentation.html. Open in session tab for user review.

Validate: Opens without errors. Navigation works (arrow keys move between slides). If fails, wrap JS in try/catch and null-check DOM refs.

</Workflow - Build>

<Workflow - Embed Assets description="Add images, QR codes, and SVG diagrams to existing slides" tools=[file_read_image, run_python, file_edit] triggers=["add an image", "embed this", "add a QR code", "put this image on slide", "add a diagram"]
>

### Step 1

[Decide] Classify the asset request:

- Image file (png, jpg, svg): base64 encode inline
- QR code: encode provided SVG data inline
- SVG diagram: create inline SVG markup from component library patterns
- Background image: base64 encode, apply as CSS background with 30-40% opacity

### Step 2

[Agent] Process the asset. For raster images, use run_python to base64 encode. For SVG diagrams, construct markup using the tree/flow patterns in references/component-library.md. For background images, wrap in a positioned div with the title-bg-img class.

### Step 3

[Agent] Use file_edit to inject the asset HTML into the target slide section. Do not modify any other slides.

Validate: Asset renders in the preview (not a broken image icon). If fails, verify mime type matches the source file format.

</Workflow - Embed Assets>

<Workflow - Iterate description="Make targeted edits based on user feedback" tools=[file_read, file_edit, open_in_session_tab] triggers=["change slide", "fix this", "update the", "move slide", "reorder", "delete slide", "add a slide"]
>

### Step 1

[Agent] Parse user feedback to identify:

- Which slide (by number or title)
- What operation (content edit, style change, reorder, delete, add)
- Scope (single slide or multiple)

### Step 2

[Agent] Execute the edit:

- Content change: edit only the target slide inner HTML
- Style change: modify CSS custom properties or add a slide-specific class
- Reorder: cut the slide section, re-insert at new position, renumber data-slide attributes
- Delete: remove the section, renumber remaining slides, update JS totalSlides
- Add: insert a new section using the appropriate layout template from references/component-library.md

Use file_edit with precise context lines. Never regenerate the full file.

Validate: Slide count matches expected total. JS totalSlides constant is correct. If fails, fix the count.

### Step 3

[Agent] Save and re-open in session tab. Confirm the change with the user.

Validate: User confirms. If fails, ask what still needs adjustment.

</Workflow - Iterate>

<Workflow - Export description="Save the final deck to a user-specified location" tools=[file_copy, run_python, file_write] triggers=["export", "save to downloads", "save the deck", "done", "finished"]
>

### Step 1

[Ask user] Where should the final file be saved? Default: ~/Downloads/

### Step 2

[Agent] Copy artifacts/presentation.html to the target path with the user's chosen filename.

If the deck has speaker notes, also extract all data-notes content and save as a companion markdown file (slide-number headings with note text beneath each).

Validate: Files exist at target paths. If fails, retry the copy.

</Workflow - Export>

Reference files loaded on demand during execution:

- references/design-tokens.md: CSS custom property system. Color palette, typography scale, spacing, borders, shadows, transitions, z-index scale. Read during Build Step 1 to get :root values.
- references/component-library.md: Eight components with full HTML markup and CSS for each. Read during Build Step 1 and Step 2 to copy patterns into slide construction.
- references/content-rules.md: The 5/5/5 rule, layout principles, speaker notes format, anti-patterns to avoid, image guidelines, file size limits. Read during Build Step 2 for validation.
- references/example-deck.html: A complete working 9-slide presentation demonstrating all components, both layout types, and the full navigation system. Read during Build Step 1 for structural reference.
- assets/deck-template.html: Minimal starter scaffold with CSS, JS navigation, and one example of each slide type. Read during Build Step 1 as the base for every new deck.
