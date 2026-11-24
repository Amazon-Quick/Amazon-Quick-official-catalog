---
description: "How a data app can reach outside origins: the content security policy, the two parts of allowing an origin, CORS, and checking the live policy."
last_updated: 2026-11-22
---
# Calling external APIs from a data app

A data app runs as a sandboxed viz extension. By default it can reach nothing outside its own
package. Read this before building anything that calls a third-party API, loads a remote image,
script, or font, or embeds outside content.

## The content security policy

Tableau serves the extension with a CSP whose `default-src` is only the package's own `content/`
path. Images are allowed from the package and `data:`. Two directives are fixed and can't be
opened up:

- `frame-src 'none'`: no iframes, so no embedded players, maps, or widgets from other sites.
- `object-src 'none'`: no plugins.

Inline scripts and `eval` are allowed. `fetch()` in `no-cors` mode is still blocked by the CSP.

## Allowing an origin takes two parts

An external origin is added to every CSP source list (`default-src`, `connect-src`, `img-src`,
`script-src`, and so on) only when **both** are true:

1. **The site allows it.** A site admin lists it under Settings > Extensions > Extension Package
   Allowed Origins. `scaffold-data-app` returns this list as `allowedOrigins`. The site setting
   alone does nothing.
2. **The package requests it.** `Packages/<package id>/manifest.json` (the JSON manifest at the
   package root, not the `.trex`) declares it in `requestedOrigins`.

The `requestedOrigins` value must be **one space-separated string**:

```json
{ "requestedOrigins": "https://accounts.example.com https://api.example.com" }
```

A JSON array is silently ignored, and so is a key named `allowedOrigins`. In both cases the CSP
falls back to package-only and every external call is blocked with no error from Tableau.

An origin is `https` + host (+ port): `https://api.example.com`. No path, query, or trailing
slash. Tableau rejects `http` and wildcard (`*`) origins at publish, and matches each requested
origin exactly against the site list.

## Origin `null` and CORS

The extension's origin is `null`, so every external request is cross-origin. Allowlisting only
gets the request past the CSP; the API must also answer with `Access-Control-Allow-Origin: *`
(or echo `null`). APIs that only allow specific origins, or send no CORS headers, can't be called
from a data app no matter what is allowlisted. The same goes for the package's own files:
`fetch()` of anything in `content/` is cross-origin and fails, because the package host sends no
CORS headers. `<script src>` and `<link>` still load.

In Amazon Quick you can't send the request that checks an API's CORS headers, because Code
Execution has no shell and no internet access. Check the API's documentation, or give the user
this command to run in a terminal on their computer:

```bash
curl -sI -X OPTIONS -H 'Origin: null' -H 'Access-Control-Request-Method: GET' https://api.example.com/<path> | grep -i access-control
```

Because there's no stable origin and pop-ups aren't available, interactive OAuth sign-in from
inside the app doesn't work. Any token has to be obtained outside the app, which raises the
issues in Security best practices in SKILL.md.

## Check the live policy

When an external call fails, find out what the CSP actually allows instead of guessing. Add this
temporarily to `app.js`, republish, and read the result on screen:

```js
document.addEventListener('securitypolicyviolation', (e) => {
  renderError(`Blocked ${e.blockedURI} by ${e.violatedDirective}. Policy: ${e.originalPolicy}`);
});
fetch('https://api.example.com/').catch((err) => renderError(`fetch failed: ${err.message}`));
```

- The origin missing from the policy means one of the two parts is missing: re-run
  `scaffold-data-app` for a fresh `allowedOrigins`, and `declare_origins.py --list` for what the
  package requests.
- The origin present in the policy but `fetch` still failing means a CORS problem on the API side.

Remove the probe before the final publish.

## Prefer not to need this

Every external origin is a dependency the site admin has to approve and a path for data to leave
Tableau. Ask whether the app really needs it before adding one; see Security best practices in
SKILL.md.
