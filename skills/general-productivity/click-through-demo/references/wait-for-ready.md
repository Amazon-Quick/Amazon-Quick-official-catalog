---
description: "How to confirm a page has finished loading before measuring or capturing it, with the browser's wait for an element only the planned screen has and a quick in-page check for loaders and pending images."
last_updated: 2026-10-27
origin: original
---

# Wait For Ready

<purpose>
Opening a page returns when the browser reports it loaded, which is often before the page's data arrives. Run both checks below after every navigation and every click, before measuring or capturing.
</purpose>

<timings>
The skill sets its wait times here and nowhere else.

| Wait | Time |
| --- | --- |
| Element wait (check 1) | 15 seconds, then once more if it times out |
| Re-wait while a loader is still visible | 10 seconds |
| Re-wait while images are still pending | 2 seconds, once |
</timings>

<check name="1-wait-for-element">
Use the Web Browser skill's wait tool with a CSS selector that only the planned screen has, such as a results row, a record's title, or a product image. When the screen changes without a new address (a filter, a tab, an expanded row), wait for text that only the new state shows. A selector that also matches the header, the footer, or the previous screen lets the wait pass before the content arrives, so pick something specific to the new content.
</check>

<check name="2-quick-check">
Then write a short synchronous script for the page and run it as its own browser call. It should count only elements the viewer can see in the viewport and return these fields.

| Field | What it holds |
| --- | --- |
| `busy` | How many loading indicators are visible, such as elements marked busy, progress bars, and elements whose class names suggest a spinner, skeleton, loader, or shimmer |
| `busy_example` | The class name or tag of the first one, so you can judge whether it is a real loader |
| `images_pending` | How many visible images have not finished loading |
| `document` | The document's ready state |
| `load_ms` | The page load time from the browser's navigation timing, or null if there is none |
| `hidden` | Whether the browser reports the tab as hidden |
| `viewport` | The viewport width, height, and device pixel ratio |
</check>

<reading_the_result>
| Result | What to do |
| --- | --- |
| `busy` is 0, `images_pending` is 0, and `document` is complete | The screen is ready. Record `load_ms` as its load time, or 0 when the screen came from typing or a filter rather than a new page. |
| `busy` is above 0 | If `busy_example` is a real loader, re-wait and run the check again. An element that never goes away, such as a permanent class that happens to contain "loader", does not block readiness. |
| `images_pending` is above 0 | Re-wait once and run the check again. Carousels and lazy images may never finish, so capture after one retry and note it in the load event's `detail`. |
| The element wait timed out twice | Ask the user what to do, as the workflow step describes. If `hidden` is true, ask them to bring the browser window to the front first, because some sites do not load content in a hidden tab. |
| `viewport` differs from the first step | Stop, per Rule 9. |
</reading_the_result>
