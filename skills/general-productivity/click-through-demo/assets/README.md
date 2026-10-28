---
description: "Turn a website into a self-contained click-through HTML demo captured from your own logged-in browser."
last_updated: 2026-10-27
origin: original
---

# Click-Through Demo

Turn a website into a self-contained click-through HTML demo captured from your own logged-in browser.

## Overview

Give the skill a starting page. It reads the site as text and offers two or three tours on one card, such as "find an experiment and open its details". After you pick one and any extras, it walks that path in your browser. It waits for each page to finish loading, measures where each click goes, and captures every screen at full resolution.

The result is one HTML file with every screenshot embedded, so it opens offline on its own. Viewers click the spotlighted spot or use the arrow keys, and a demo can have chapters, intro and closing cards, zoom on small targets, blurred personal information, and videos or images on any step. Next to the demo, the skill keeps demo.json, a small working file with each step's text, highlight, and blur areas. Later edits work from that file, so they never need new screenshots.

The skill only looks around. It never submits, sends, saves, deletes, buys, or changes settings, and it never types passwords.

## Pre-requisites

| Dependency | Type | Runs on | Required |
| --- | --- | --- | --- |
| Amazon Quick Web Browser skill | System tool | Your computer, through the Amazon Quick desktop app, driving the browser chosen in Amazon Quick settings | Required |
| Permission to run page scripts and type into pages | Browser permission prompts in Amazon Quick | Your computer | Required. Choose Allow when the skill first measures a page, because that is how highlights and blur areas are measured. Choose Allow when it first types a search term, or the tour skips the typed-search screen. |
| A trusted folder on your computer | Amazon Quick allowed folder | Your computer | Recommended. The skill lists your folders and saves the demo in one, so it opens in your browser with internet access. Add one under allowed folders in Amazon Quick settings. |
| Signed-in session on the site you demo | Your own browser login | Your computer | Optional. Needed only for pages behind a login. Sign in yourself, since the skill never types passwords. |

The skill's scripts need Pillow and pydantic, which the Amazon Quick sandbox provides. Video links (direct https .mp4 or .webm) need an internet connection when the demo is viewed, and embedded video files do not.

## Installation

1. In Amazon Quick on desktop, go to Customize > Skills, choose Browse all, select the Official tab, and search for the skill by name. Choose Install. See [Browsing for more skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html).
2. While the skill runs, keep the Amazon Quick desktop app open, your computer awake, and the browser window in front on one display. Some sites do not load content in a hidden tab. Pick your browser in Amazon Quick settings. For desktop setup, see [Connections on desktop](https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html).

## Getting started

Say `ctd help` for the menu, or try the tested example.

```
Make a click-through demo of https://www.amazon.com/ that shows how to search for a product and open it, with personal info blurred.
```

To change a demo, say `ctd edit`. You can also open demo.json in a text editor, change any title, caption, highlight, or blur area, save it, and say "I edited demo.json, rebuild it". The rebuild checks every field and tells you what to fix if something is wrong.

To see a finished demo first, say `ctd example`, or open `assets/examples/amazon-search/index.html` from the skill folder in your browser. That demo came from the prompt above, and `references/examples/amazon-search.md` shows the plan and settings behind it.
