---
inclusion: always
name: quick-sandbox-code-standards
description: "Runtime rules for code generated to run in the Amazon Quick sandbox (run_python and run_javascript): manifest-only dependencies, no network, time and memory limits, workspace persistence, read-only vs write execution, result handling, imports, regexes, and filtering. Applies to both languages."
scope: language-agnostic
created_date: 2026-09-13
last_updated: 2026-09-13
origin: original
---

<purpose>
Runtime and hygiene rules every snippet generated for the Amazon Quick sandbox must follow, in either language. The Python and JavaScript companion docs cover language syntax; this covers the shared runtime, imports, regexes, and filtering.
</purpose>

<rules>
1. Import only dependencies listed in the applicable manifest (quick-sandbox-requirements.txt for Python, quick-sandbox-package.json for JavaScript). Never install packages at runtime.
2. Never make network calls from code. Pass external data in through a tool or connector.
3. Split long work into bounded chunks and write each unit to WORKSPACE_DIR as it completes. Execution is time-limited, and in-memory state does not survive across separate calls.
4. Use run_python by default. Use run_python_with_write only when the code must create, modify, or delete files in allowed folders.
5. Print every result the agent needs. Unprinted output is not returned.
6. Print a tool result's type and structure before indexing into it, then parse against the observed shape, not a guessed key.
7. Place all imports at the top of the file. Never import inside a function, class, or branch.
8. Use native string methods (contains, prefix, split, replace) for fixed substrings and static text. Use a regex only for a genuinely variable pattern.
9. Keep regex patterns simple and anchored. Do not nest quantifiers, which cause catastrophic backtracking.
10. Use non-capturing groups unless the captured text is used.
11. Compile a regex once and reuse it when filtering many items, rather than recompiling per item.
12. Write a filter as a named predicate or a clear comprehension, not a dense chained one-liner.
13. Keep credentials and tokens out of code. Tools and connectors handle authentication.
14. Build every filesystem path with the language's path utilities (Python pathlib, Node path). Never concatenate path strings or hardcode a separator, a drive letter, or a case-sensitive-filename assumption, so a script runs on both Windows and macOS.
</rules>

<examples>
<example type="correct">
```python
import json
import os
import re

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # compiled once, anchored (Rules 9, 11)

def is_active(record: dict) -> bool:  # named predicate (Rule 12)
    return record.get("status") == "active"

records = json.load(open(os.path.join(os.environ["WORKSPACE_DIR"], "in.json")))
active = [r for r in records if is_active(r) and ISO_DATE.match(r["date"])]
print(f"{len(active)} active records")  # print the result (Rule 5)
```
</example>

<example type="incorrect">
```python
# import mid-function (7), regex for a plain substring (8), nested quantifier (9),
# needless capture (10), recompiled per item (12), dense filter (12).
def filter_rows(records):
    import re
    return [r for r in records
            if re.compile(r"(\w+)+@").search(r["email"]) and re.search(r".*(active).*", r["status"])]
```
</example>
</examples>

<references>
- #[[file:references/quick-sandbox-requirements.txt]] - Python package manifest
- #[[file:references/quick-sandbox-package.json]] - JavaScript module manifest
- #[[file:references/python-sandbox-code-standards.md]] - Python syntax rules
- #[[file:references/javascript-sandbox-code-standards.md]] - JavaScript syntax rules
- https://docs.python.org/3/library/pathlib.html - Python pathlib
- https://nodejs.org/api/path.html - Node path
</references>
