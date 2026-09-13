---
inclusion: fileMatch
fileMatchPattern: ["**/*.js", "**/*.mjs", "**/*.cjs"]
name: javascript-sandbox-code-standards
description: "Readable, correct JavaScript for the Amazon Quick sandbox: const/let over var, named exports, allowed modules only, structured data, disciplined async and errors, no dynamic code evaluation. Companion to quick-sandbox-code-standards."
scope: typescript
created_date: 2026-09-13
last_updated: 2026-09-13
origin: original
---

<purpose>
JavaScript syntax and correctness rules for the Amazon Quick sandbox. Shared runtime rules live in quick-sandbox-code-standards.
</purpose>

<rules>
1. Declare bindings with const, or let when reassignment is required. Never var.
2. Import only modules listed in quick-sandbox-package.json (its packages and allowed_modules).
3. Use named exports, not default exports.
4. Never use eval or the Function constructor to run code from a string.
5. Return a promise from every async function, and never mix callbacks with promises. Consume async iterables with for-await-of.
6. Bound every long-running loop, and use Promise.allSettled where one failure must not abort the batch.
7. Wrap only the statement that can throw, and inspect the caught value before use. No empty catch.
8. Build a structured object in one shape, not an empty object mutated field by field.
9. Keep credentials and tokens out of code. Tools and connectors handle authentication.
10. Reach the workspace through the WORKSPACE_DIR global and the allowed path and fs modules.
</rules>

<examples>
<example type="correct">
```javascript
import { writeFile } from "fs/promises";
import path from "path";

export async function writeRows(rows) {
  const outPath = path.join(process.env.WORKSPACE_DIR, "rows.json");
  await writeFile(outPath, JSON.stringify(rows), "utf-8");
  return outPath;
}
```
</example>

<example type="incorrect">
```javascript
// var (1), dynamic evaluation (4), default export (3), empty catch (7).
var parse = new Function("s", "return eval(s)");
export default async function run(input) {
  try {
    return parse(input);
  } catch (e) {}
}
```
</example>
</examples>

<references>
- #[[file:references/quick-sandbox-code-standards.md]] - Shared runtime rules
- #[[file:references/quick-sandbox-package.json]] - JavaScript module manifest
- https://nodejs.org/api/ - Node.js API
</references>
