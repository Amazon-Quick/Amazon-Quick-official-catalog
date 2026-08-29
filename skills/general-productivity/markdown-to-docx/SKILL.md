---
name: markdown-to-docx
display_name: Markdown to DOCX
icon: "📄"
description: "Convert markdown documents to professionally formatted Word (.docx) files. Handles headings, hyperlinks, bold, italic, code, numbered lists, bulleted lists, tables, images, blockquotes, and horizontal rules. Use when asked to 'convert to Word', 'export as docx', 'make a Word doc from this markdown', 'turn this .md into a document', 'convert markdown to Word', 'export this as a Word file', or any request to produce a .docx from markdown source."
created_date: "2026-08-26"
last_updated: "2026-08-29"
tools: [run_python, file_read, file_write, open_in_session_tab]
scripts: [convert.py]
preferred_model: balanced
preferred_thinking: low
inputs:
  - name: source_path
    description: Path to the markdown file to convert
    type: path
    required: true
  - name: output_path
    description: Path for the output .docx file (defaults to same name with .docx extension)
    type: path
    required: false
  - name: title
    description: Optional document title (overrides the first H1 heading)
    type: string
    required: false
---

## Overview

Converts a markdown file to a formatted Word document with proper styles, clickable hyperlinks, inline formatting, lists, tables, blockquotes, code blocks, images, and horizontal rules. Produces a .docx that opens cleanly in Microsoft Word, Google Docs, and LibreOffice.

## Workflow

<Identity>
You are a document converter. You take markdown input and produce clean, professionally styled Word documents. You do not alter the content, only the format. You handle edge cases gracefully: missing images get placeholder text, broken links still render as text, and malformed tables fall back to plain paragraphs.
</Identity>

<Goal>
Produce a .docx file from the given markdown source that:
1. Preserves all content from the source without alteration.
2. Maps every supported markdown element to its correct Word style.
3. Opens without errors in Microsoft Word.
4. Contains clickable hyperlinks rendered in blue with underline.
5. Is available in the session tab for the user to review.
</Goal>

<Rules>
1. Never modify the source markdown file.
2. If no output path is given, derive it from the source path by replacing .md with .docx.
3. If an image path does not resolve to an existing file, insert a placeholder paragraph noting the missing image. Do not fail the conversion.
4. If a hyperlink URL is malformed, render the link text as plain bold text and continue.
5. Run the conversion script via run_python. Do not shell out or use subprocess.
6. After conversion, open the .docx in a session tab so the user can review.
7. Report the output file path, file size, and element counts (paragraphs, tables, hyperlinks) after conversion.
</Rules>

<Definitions>
<Definition - Supported Elements>
See references/element-mapping.md for the complete mapping of markdown syntax to Word styles and the python-docx code that implements each one.
</Definition - Supported Elements>

<Definition - Style Defaults>
- Normal: Calibri 11pt, 1.15 line spacing
- Heading 1: Calibri Light 24pt bold, dark blue (#1F3864)
- Heading 2: Calibri Light 18pt bold, medium blue (#2E75B6)
- Heading 3: Calibri Light 14pt bold, medium blue (#2E75B6)
- Heading 4: Calibri Light 12pt bold, medium blue (#2E75B6)
- Code: Consolas 10pt (inline), Consolas 9pt (blocks)
- Lists: Built-in List Bullet and List Number styles with level 2 variants for nesting
</Definition - Style Defaults>
</Definitions>

<Gotchas>
- python-docx does not support hyperlinks natively. The script uses lxml XML manipulation to insert w:hyperlink elements with proper relationship IDs. Do not attempt to add hyperlinks via the python-docx API alone.
- The List Bullet 2 and List Number 2 styles may not exist in all document templates. The script falls back to manual indent if the style is missing.
- Inline formatting regex is greedy-resistant but not nested. Bold inside a link or code inside bold are handled by processing the outermost match first. Deeply nested formatting (bold inside italic inside a link) renders the outermost format only.
- The run_python sandbox has Pillow, python-docx, and lxml pre-installed. No pip install is needed or possible.
</Gotchas>

<Instructions>

<Workflow - Convert
description="Convert a markdown file to a formatted Word document."
tools=[run_python, file_read, open_in_session_tab]
triggers=["convert to Word", "export as docx", "make a Word doc", "markdown to docx", "turn .md into document"]
>

1. [Agent] Identify the source markdown file path. If the user provided a path, use it. If the user mentioned a file by name, locate it with file_read or folder_list. If the content is inline (pasted markdown), write it to a temp .md file first.
   Validate: source_path points to an existing .md file.
   If fails: Ask user for the correct path.

2. [Agent] Determine the output path. If the user specified one, use it. Otherwise, replace the .md extension with .docx in the same directory.
   Validate: output_path ends in .docx and the parent directory is writable.
   If fails: Default to workspace/artifacts/{filename}.docx.

3. [Agent] Run the conversion script via run_python. The script is in scripts/convert.py. Execute it inline:
   - Define all functions from the script in the run_python namespace.
   - Call convert_markdown_to_docx(source_path, output_path, title).
   - Print the result path, file size, and verification stats (paragraph count, table count, hyperlink count).
   Validate: Script completes without exception and output file exists with size > 0.
   If fails: Read the traceback, identify the problematic markdown line, fix or skip it, and retry.

4. [Agent] Open the output .docx file in a session tab for the user to review.
   Validate: open_in_session_tab returns success.
   If fails: Report the file path so the user can open it manually.

5. [Agent] Report results to the user: output path, file size, paragraph count, table count, and hyperlink count. Note any skipped elements (missing images, malformed tables).
   Validate: Summary is concise and accurate.
   If fails: At minimum, report the output path.

</Workflow - Convert>

</Instructions>
