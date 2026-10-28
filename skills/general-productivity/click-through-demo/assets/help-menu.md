**Click-Through Demo commands**

| Command | What it does |
| --- | --- |
| `ctd help` | Show this menu. |
| `ctd build` | Scout a site, pick a tour on one card, and turn it into a click-through demo captured from your browser. |
| `ctd edit` | Change a demo's text, cards, chapters, videos, images, blur, zoom, length, or file size without recapturing, or rebuild it after you edit demo.json yourself. |
| `ctd example` | Open a finished example demo (Amazon.com search) with the prompt that built it, then help you build your own. |

**Try the tested example**

```
Make a click-through demo of https://www.amazon.com/ that shows how to search for a product and open it, with personal info blurred.
```

This prompt builds a 4-screen tour through the home page, a typed search, the results, and a product page. The tour stops at Add to cart without clicking it, and it blurs your name, address, cart, and recommendations. The finished demo is at `assets/examples/amazon-search/index.html`, with its plan and settings in `references/examples/amazon-search.md`.

Say a command to start, or describe what you want in your own words.
