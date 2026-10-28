---
description: "How to write a demo's titles, captions, and actions, when to use zoom, blur, and media, and what the viewer template already does."
last_updated: 2026-10-27
origin: original
---

# Viewer Design

<text>
| Text | How to write it |
| --- | --- |
| Title | Under 8 words, naming what the screen shows |
| Caption | One or two plain-text sentences about what is visible on this screen |
| Action | Starts with a verb and names the control, such as "Open the first record". The last screen has no action. |
</text>

<extras>
Use zoom on small targets so viewers can see what to click, and blur on personal and account information. Blur cannot be undone in the built file, because the pixels are replaced.

Add media only where it explains something the screen cannot, such as a short video on the first or last screen. An embedded video file plays offline, which makes it a better choice than a video link. Chapters, an intro card, and a closing card with one call to action suit longer tours, per the planning section of <Resource key="scout-and-plan">.
</extras>

<template_handles>
assets/demo-template.html already draws the spotlight and its pulsing ring, places the tooltip and its arrow, zooms toward the hotspot, and shows a progress bar and step menu grouped by chapter. It also renders intro and closing cards, shows images and videos in the tooltip, and supports full screen, keyboard navigation, a link to each step (`#step-3`), reduced motion, and dark mode. All text goes in as plain text. None of this needs agent work.
</template_handles>
