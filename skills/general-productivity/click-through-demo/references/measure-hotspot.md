---
description: "How to measure the element the viewer clicks next as a hotspot in viewport percentages, and how to find visible personal information to blur, in one in-page call per screen."
last_updated: 2026-10-27
origin: original
---

# Measure Hotspot

<purpose>
A hotspot has to sit exactly on the element the viewer clicks next, so it comes from the live page rather than from a screenshot. On every screen, wait for it to be ready (<Resource key="wait-for-ready">), run one measurement call, and take the screenshot straight away with no scrolling in between.
</purpose>

<approach>
Write one short synchronous script for the page that does both jobs below, and run it as its own browser call. Build it fresh for each screen from what the page state shows, rather than from a selector you remember, because sites change their markup.

Find the target first.
1. Pick it by its link address when the action follows a link, or by a CSS selector plus the start of its visible text when it is a button, tab, row, or field. Text is what picks one item out of a list.
2. Keep only visible matches. If more than one remains, choose by position or by longer text, and report how many matched.
3. If the target is not fully in the viewport, scroll it into view first, then measure, because the screenshot follows straight after.
4. Mark it with a `data-ctd-target` attribute, removing that attribute from any earlier target, so it can be clicked again without a new search.
5. Decide how the action happens. A real link address (not `#` and not a `javascript:` address) means navigate to it. Anything else means click it.

Then measure. Take the element's bounding rectangle, add a few pixels of padding on each side, and divide each edge by the viewport width or height to get percentages. Clamp the result so the box stays between 0 and 100 and never runs past an edge, because the build rejects one that does. Use more padding when the box frames an area of interest rather than a click target. When the target is tiny, suggest a zoom so viewers can see it, staying within 1 to 3. A zoom of 1.5 to 2 usually works.

Find personal information in the same call, and measure each match the same way.
- Text containing the user's name, username, or the address or postcode the site shows. Read these from the page on this run, never from an example or another user.
- Email addresses.
- Avatar and profile images.
- Elements that show account details, such as a cart count or an account menu, when the page state shows them.
- Sections built from the user's history, found by their headings. Wording such as "Recently viewed", "Based on your", "Because you", "Buy it again", and "Recommended for you" is common. Add the site's own wording when you see it, and blur the whole section rather than its heading alone.
</approach>

<result>
Return these fields so the workflow steps can rely on them.

| Field | What it holds |
| --- | --- |
| `found` | Whether a visible target matched |
| `matches` | How many visible elements matched |
| `text` | The chosen target's visible text, trimmed |
| `href` | The link address when the action is to navigate, otherwise null |
| `act_by` | `navigate` or `click` |
| `hotspot` | `x`, `y`, `w`, `h` in viewport percentages, and the suggested `zoom` |
| `blurs` | A list of rectangles in the same percentages, each with a short `reason` such as "avatar" or "name or address" |
| `viewport` | The viewport width, height, and device pixel ratio |
</result>

<reading_the_result>
| Result | What to do |
| --- | --- |
| `found` is false | Loosen the text, try another selector, or check that the screen is ready. |
| `matches` is above 1 and `text` is not the planned element | Choose by position or a longer text. In a list, an item's first heading is often a brand or category rather than its title, so match the title link by its text. |
| `act_by` is `navigate` | Navigate to `href`. |
| `act_by` is `click` | Click the element whose text matches, by its number in the latest page state. If none matches, click the element marked `data-ctd-target`. |
| `hotspot` | Copy it unchanged into the step. Set `zoom` to 1 if the user turned zoom off. A control drawn as an invisible input over a styled element still measures correctly. |
| `blurs` | Add each one to the step when blur is on. Then look at the screenshot for what a script cannot know, such as recommendation rows under unfamiliar headings or account-only controls, and add blur areas for them. Name each in the delivery message. |
</reading_the_result>
