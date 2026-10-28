---
description: "A worked example of a store search demo on Amazon.com, with the prompt, the approved plan, the selectors and blur settings used, and the first change set."
last_updated: 2026-10-27
origin: original
---

# Example: Amazon.com Search Demo

<purpose>
This tested run of <Workflow - Build Demo> covers a signed-in store. Read it before building a demo of a store, a search-driven site, or any site with personal details in its header. Copy its shape rather than its values, because selectors change and have to be measured again on every run.
</purpose>

<prompt>
```
Make a click-through demo of https://www.amazon.com/ that shows how to search for a product and open it, with personal info blurred.
```

On the approval card the user chose tour 1, "Search and open a product". They added intro and closing cards, zoom on small targets, and blur, and picked a trusted folder the skill had listed.
</prompt>

<plan>
The tour has four screens in two chapters and ends before the first irreversible action, Add to cart. Typing and submitting are separate steps, so the typed search term gets its own screen.

| Step | Chapter | Screen | Action to next screen |
| --- | --- | --- | --- |
| 1 | Search | Home page | Type "kindle" in the search box |
| 2 | Search | Home page with the term typed and suggestions open | Click the search button |
| 3 | Choose a product | Search results | Open the Kindle 16 GB result |
| 4 | Choose a product | Product page, with Add to cart as the area of interest | None, because the demo stops here |
</plan>

<settings>
| Step | Waited for | Hotspot target | How the action was done |
| --- | --- | --- | --- |
| 1 | `#twotabsearchtextbox` | The search box, `#twotabsearchtextbox` | Typed into the box by element number |
| 2 | Nothing, since the page did not change | The search button, `#nav-search-submit-button` | Clicked by element number |
| 3 | `div[data-component-type='s-search-result'] h2` | The result link whose text starts with "Kindle 16 GB" | Navigated to its address |
| 4 | `#landingImage` | `#add-to-cart-button`, with extra padding | None, because the action is irreversible |

Blur covered the user's first name and delivery postcode read from the header, the cart count (`#nav-cart-count`), and history-based sections. One extra blur area went across the "Recommended deals for you" row after a look at the screenshot, because no heading rule had caught it.
</settings>

<site_notes>
- The first `h2` in a search result is the brand, not the product title, so the result link was matched by its text.
- Add to cart is an invisible input over a styled element, and its measured rectangle was still correct.
</site_notes>

<change_set>
This is the first change set, applied before capturing.

```json
{
  "demo": {
    "title": "Find a product on Amazon",
    "start_url": "https://www.amazon.com/",
    "goal": "Search for a Kindle and open its product page",
    "intro_title": "Find a product on Amazon in three clicks",
    "intro_body": "See how to search the store, scan the results, and open a product page.",
    "outro_title": "That's the whole path",
    "outro_body": "Search, pick a result, and the product page has everything you need to decide.",
    "cta_label": "Shop on Amazon",
    "cta_url": "https://www.amazon.com/",
    "accent": "#ff9900"
  },
  "chapters": [{"position": 1, "title": "Search"}, {"position": 2, "title": "Choose a product"}]
}
```

Each step then got its own change set straight after its screenshot, in the format in <Resource key="demo-store">. A later `ctd edit` added an embedded video file to step 4 without recapturing.
</change_set>

<output>
The finished demo is bundled at `assets/examples/amazon-search/index.html`. Only the blurred index.html ships with the skill, because the raw screenshots, demo.json, and hotspot-check.png hold the unblurred originals with the capturing user's account details.
</output>
