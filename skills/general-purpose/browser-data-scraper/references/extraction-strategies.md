# Extraction Strategies (fetch-based)

These strategies work on content retrieved with url_fetch. Quick provides no
headless browser, so anything that requires clicking, scrolling, or intercepting
network requests is out of scope. Check strategies in priority order and use the
first one whose detection signal is present.

## Strategy priority

| Priority | Strategy | Detection signal | Method |
|----------|----------|-------------------|--------|
| 1 | URL parameter manipulation | The URL contains `?page=N`, `?offset=M`, `?p=N`, `?start=K`, or a similar query parameter, and changing it changes the content. | Increment the parameter programmatically, build each page URL, and fetch it with url_fetch. |
| 2 | Semantic pagination links | The fetched HTML contains a next-page link (see Semantic selector priority below). | Resolve the next URL from the link's href (make it absolute), then fetch it. Repeat until no next link. |
| 3 | Sitemap or link discovery | The input is a `sitemap.xml`, or the start page lists same-domain content links. | Parse the sitemap or the anchor tags into a URL list, filter it, then fetch each URL. |
| 4 | Single page | No pagination signal is present. | Extract once from the single fetched page. |

## Semantic selector priority

When looking for the next-page link in fetched HTML, check in this order and use
the first match. Parse with beautifulsoup4 or lxml.

1. `<link rel="next">` or `<a rel="next">`: the W3C standard, most reliable.
2. An anchor whose `aria-label` contains "Next", "Next Page", or "Forward".
3. A `role="navigation"` or `<nav>` container whose child links match page patterns.
4. Link text matching keywords: Next, Continue, Forward, More.
5. Link text matching symbols: `>`, `>>`, `→`, `›`.
6. Numbered page links: infer the next number from the current page's position.

Filter every candidate: the resolved href must be an absolute URL on the same
site that differs from the current URL only by a page or offset value. Discard
links that point off-domain or back to the current page.

## Detecting client-side rendering

If a fetched page returns little or no content, or the target fields described in
`{{target_data}}` are entirely absent from what url_fetch returned, the site most
likely renders its content with JavaScript in the browser. url_fetch cannot
execute JavaScript, so this content is unreachable with available tools. Stop and
tell the user plainly (Rule 10). Do not invent records to fill the gap.

## Volume estimation

Look in the fetched content for a total-count indicator such as
"Showing 1-20 of 450 results". Divide the total by the items-per-page to estimate
the page count. When no indicator exists, state that the total is unknown and rely
on the termination conditions in the Full Extraction workflow (three consecutive
pages with no new records, a 429 or block page, or max_pages).

## Parsing and export notes

- Parse HTML with beautifulsoup4 or lxml. If url_fetch already returned clean
  reader text instead of HTML, reason over the text directly to pull fields.
- Compute each record's content hash with hashlib.sha256 over the record's data
  fields (excluding `_meta`), serialized with sorted keys, so the same record
  always yields the same hash regardless of key order.
- Write JSONL one object per line and flush after each page so a sandbox timeout
  or interruption never loses completed pages.
- For CSV export use the standard library csv module. For XLSX use XlsxWriter.
  Both are available in the sandbox; pandas is also available if a dataframe
  step is convenient. Never import a package outside the pre-installed set.
