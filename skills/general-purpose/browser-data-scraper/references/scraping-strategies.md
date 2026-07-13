# Traversal Strategies

This skill reads static HTML through the url_fetch tool. It cannot run a browser or
execute JavaScript, so it supports only the strategies that work by fetching URLs and
parsing the returned HTML. Read this file during reconnaissance, detect the mechanism in
priority order, and pick the first supported strategy whose detection signal is present.
If the chosen strategy fails mid-scrape, fall back to the next supported one before giving up.

## Supported strategies (priority order)

| Priority | Strategy | Detection signal | Method |
|----------|----------|------------------|--------|
| 1 | URL Parameter Manipulation | The URL contains `?page=N`, `?offset=M`, `?p=N`, or a similar query parameter, and changing it changes the content | Increment the parameter and fetch each resulting URL with url_fetch |
| 2 | Next-Link Following | The fetched HTML contains a next-page link (see Selector Priority below) | Read the next link's href from the parsed HTML, fetch it, repeat until no next link is present |
| 3 | Recursive Filtering | Pagination is capped (for example only the first 100 pages are reachable) but filter parameters exist (date, category, region) | Split the dataset by a filter parameter into sub-queries, each with its own pagination, so every sub-query stays under the cap |
| 4 | Sitemap Discovery | The input is a sitemap.xml, or the site exposes one | Parse the sitemap for content URLs, filter them, then fetch each (handled by Crawl Mode and URL List Mode) |
| 5 | Single Page | No pagination signal and all target records are on one page | Extract once; no traversal needed |

## Next-link selector priority

When locating the next-page link in parsed HTML, check in this order and take the first match:

1. `<a rel="next">` or `<link rel="next">` (the W3C standard, most reliable).
2. An anchor whose `aria-label` contains "Next", "Next Page", or "Forward".
3. Anchors inside a `role="navigation"` or `<nav>` pagination container whose href matches a page or offset pattern.
4. Anchor text matching a keyword: Next, Continue, Forward, More.
5. Anchor text matching a symbol: >, >>, or a right-pointing arrow.
6. A numbered page link one greater than the current page, inferred from the pagination list.

Filter candidates: the link must resolve to an absolute URL that differs from the current
page only by a page or offset value. Discard links that point off-domain or back to the
same page.

## Out of scope: strategies that require a live browser

These appeared in the source workflow but depend on a scriptable browser or a network
inspector, neither of which is available. Do not attempt them. If a target only exposes its
data through one of these, tell the user the page needs a browser and is out of scope.

- API interception via the network tab: reading XHR or fetch traffic to call a backend
  JSON endpoint directly. There is no network inspector; url_fetch cannot observe a page's
  runtime requests.
- Infinite scroll: content that loads only as the page is scrolled. Fetching the URL
  returns just the initial batch; there is no scroll event without a browser.
- Load More button: content appended by clicking a button. There is no way to trigger the
  click, so only the pre-click content is present in the fetched HTML.
- Any JavaScript-rendered content: single-page apps (React, Vue, Angular) that build the
  DOM client-side return an empty shell to url_fetch. Detect this when no repeating data
  pattern is found in the fetched HTML.
