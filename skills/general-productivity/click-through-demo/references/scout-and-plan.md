---
description: "How to read a site as text before capturing anything, turn what it shows into two or three tours, and ask for approval on one card."
last_updated: 2026-10-27
origin: original
---

# Scout and Plan

<purpose>
Screenshots are the slow, costly part of a run. Reading pages as text first lets the user approve one concrete tour before anything is captured, and the user never has to name a link or a selector.
</purpose>

<budget>
- Read at most 3 pages, the start page and the 2 that look most like the main path.
- Read text only, with no screenshots and no image reads.
- Wait for each page to be ready first (<Resource key="wait-for-ready">), so a slow page is not scouted empty.
</budget>

<what_to_read>
After a wait, the browser returns the page state with its visible links and controls. Plan from that first.

When it is not enough, write a short synchronous script for the page and run it as its own browser call. Keep its output small by returning only visible items, one entry per link address, and labels trimmed to a few words. Collect what the plan needs.

| Look for | Why it matters |
| --- | --- |
| Headings | They name what each page is about, which gives tours their titles. |
| Links, with their text, address, and page zone (header, navigation, main content, footer) | Tours should run through the main content, not the header or footer. |
| Buttons, tabs, filters, menus, and search boxes | These change what is on screen without a new page, and make good steps. |
| Table rows or cards that open something on click but are not links | Plan to click them, because there is no address to navigate to. |
| Forms, and whether each one is a search | A search is look-only. Any other form submit is irreversible and ends the tour. |
| An avatar or an account or profile control | The user is signed in, so recommend blur on the approval card. |
</what_to_read>

<planning>
Turn what you read into 2 or 3 tours. A good tour answers one question a viewer would have, such as "how do I find X" or "what does Y show me". A tour that tries to cover a whole product should become two demos.

Keep each tour to 3 to 5 screens by default and never more than {{max_steps}}. Use only look-only actions between screens, and end on the screen that shows the payoff (the record, the result, or the setting) with an area of interest on it. Once a tour reaches 6 screens or more, group them into 2 or 3 chapters named for what the viewer does in each.

Prefer paths that change what is on screen, such as filtering, opening a record, or switching a tab, over paths that move between similar pages. When the user named a goal or steps, make that tour the first option.
</planning>

<approval_card>
Ask once, in one grouped card of at most 3 questions, with the recommended choice first and every default already chosen.

| Question | Options |
| --- | --- |
| Which tour | The 2 or 3 tours, each with its screens in one line (for example "Results table, filter by year, open a record, read its details"), then Other |
| Extras (multi-select) | Intro and closing cards, zoom on small targets, blur personal information (recommended when the user is signed in), a closing button that links to a page, a video or image on a step |
| Where to save | Each trusted folder on the user's computer by name, with a new subfolder named for the tour inside the first one recommended, then the session's artifacts folder (preview only, see Rule 15), then Other |
</approval_card>
