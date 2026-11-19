---
description: "Readable, correct JavaScript for the AWS Quick code sandbox: how run_javascript runs a script, require for allowed modules only, one self-contained file per script, an entry function called with its arguments, const/let, structured data, disciplined async and errors, and no dynamic code evaluation. Companion to quick-sandbox-code-standards."
last_updated: 2026-11-18
---

<purpose>
JavaScript syntax and correctness rules for the code sandbox. Shared runtime rules live in quick-sandbox-code-standards.
</purpose>

<rules>
1. Declare bindings with const, or let when reassignment is required. Never var.
2. Load modules with `require`. run_javascript runs a file's code inside an async function in a Node.js `vm` context, so `import` and `export` statements are a syntax error there, and its `require` accepts only the module names in quick-sandbox-package.json.
3. Keep each script one self-contained file. `require` can't load another script from the skill's `scripts/` folder, so a script defines every function it uses.
4. Give a runnable script a verb_noun name from the standard prefix set (create_, check_, find_, run_) and one async entry function, `main`, that takes a single object of named arguments and returns its result. run_javascript has no arguments parameter: run the script with `file=` and call `main` in `code=`, which runs after the file in the same call, for example `console.log(JSON.stringify(await main({ path: "data/in.json" })))`.
5. Never use eval or the Function constructor to run code from a string. The sandbox disables both.
6. Return a promise from every async function, and never mix callbacks with promises. Consume async iterables with for-await-of.
7. Bound every long-running loop, and use Promise.allSettled where one failure must not abort the batch.
8. Wrap only the statement that can throw, and inspect the caught value before use. No empty catch.
9. Build a structured object in one shape, not an empty object mutated field by field.
10. Keep credentials and tokens out of code. Tools and connectors handle authentication.
11. Reach the workspace through the WORKSPACE_DIR global and the allowed path and fs modules. Only console output comes back to the agent, so log every result it needs.
</rules>

<examples>
<example type="correct">
```javascript
/**
 * description: Write rows to a JSON file in the workspace and return its path.
 * last_updated: 2026-11-18
 */
// Run with file="scripts/write_rows.js" and
// code='console.log(await main({ rows: [{ a: 1 }] }))' (Rules 2, 4, 11).
const { writeFile } = require("fs/promises");
const path = require("path");

async function main({ rows }) {
  const outPath = path.join(WORKSPACE_DIR, "rows.json");
  await writeFile(outPath, JSON.stringify(rows), "utf-8");
  return outPath;
}
```
</example>

<example type="incorrect">
```javascript
// import and export (2), a sibling script (3), var (1), dynamic evaluation (5),
// empty catch (8).
import { helper } from "./helper.js";
var parse = new Function("s", "return eval(s)");
export default async function run(input) {
  try {
    return parse(helper(input));
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
