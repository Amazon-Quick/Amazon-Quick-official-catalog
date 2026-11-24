---
description: "What to check when a downloaded .twbx may be incomplete, and how the staged workbook upload works."
last_updated: 2026-11-22
---
# Package fallbacks

Read only when package completeness is uncertain or a packaged dependency is
missing.

## TWBX completeness

1. Check the archive with `zipfile.ZipFile(path).testzip()` in Code
   Execution and require `None`, which means every member is intact.
2. List archive members and inspect the root TWB's local `dbname` and
   `filename` references.
3. Confirm every referenced Hyper or local file exists at the expected archive
   path.
4. Treat a bare opaque identifier used as a Hyper `dbname`, or a missing
   referenced path, as incomplete.
5. Re-download with `includeExtract: true` when incomplete. Do not invent or
   rewrite a missing dependency path.
6. Hand off the verified TWBX, not the extracted TWB alone, whenever packaged
   dependencies exist.

XSD validation establishes TWB structure; it does not establish package
completeness.

## Staged upload

In Amazon Quick the staged upload can't be completed: the file would have to
be sent to the link `request-workbook-upload` returns with an HTTP PUT, and
nothing in Quick can send one. Don't call `request-workbook-upload` or
`publish-workbook`; hand the file to the user as `SKILL.md`'s "Validate and
hand off" section describes.
