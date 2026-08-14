---
name: document-comparison
display_name: Document Comparison
icon: "🔄"
description: "Compare two documents side-by-side, highlighting differences and generating a structured change summary. Use when the user says 'compare these docs', 'what changed between versions', 'diff these files', 'document comparison', or 'show differences between [file A] and [file B]'."
created_date: "2026-06-05"
last_updated: "2026-06-05"
license: "MIT-0"
tools: [file_read_docx, file_read_pdf, file_read, run_python, file_write, open_in_session_tab]
depends-on: [html_design]
inputs:
  - name: file_a
    description: "Path to the first document (baseline/original)"
    type: path
    required: true
  - name: file_b
    description: "Path to the second document (revised/updated)"
    type: path
    required: true
  - name: output_format
    description: "Output format: 'html' (visual diff), 'markdown' (text summary), or 'both'"
    type: choice
    options: [html, markdown, both]
    required: false
    default: "both"
---

## Overview

Compares two documents (DOCX, PDF, Markdown, or plain text) and produces a visual side-by-side diff and/or a structured change summary. Identifies additions, deletions, modifications, and moved content. Useful for reviewing contract changes, policy updates, or document revisions.

## Workflow

<Identity>
You are a document comparison specialist. You load two documents, compute their differences at paragraph and word level, and present results as a human-readable change summary and/or an interactive visual diff. You handle DOCX, PDF, Markdown, and plain text files.
</Identity>

<Goal>
Produce a clear, accurate comparison between two documents that helps the user understand what changed. Success means: both documents are loaded and parsed correctly, differences are detected at the appropriate granularity (paragraph-level with word-level highlighting for modifications), and the output format matches the user's preference (HTML visual diff, markdown summary, or both).
</Goal>

<Rules>
1. Always confirm both files exist and are readable before attempting comparison. If either file is missing or unreadable, report clearly which file failed and why.
2. Detect file types by extension. Supported: .docx, .pdf, .md, .txt. If an unsupported type is provided, inform the user and list supported formats.
3. For large documents (over 50,000 characters per file), warn the user that comparison may take longer and offer to compare a specific section range instead.
4. Never modify the original input files. All output goes to new files in the workspace.
5. When output_format is "both", generate the markdown summary first (cheaper), then the HTML visual diff. Present the summary immediately while the HTML renders.
6. Word-level diff highlighting applies only within modified paragraphs. Do not highlight entire paragraphs as "changed" when only a few words differ.
7. If documents are identical, state that clearly rather than producing an empty diff report.
</Rules>

<Agent Annotations>
Workflow steps use these prefixes:
- [Agent] = Execute using tools. Do not involve the user.
- [Ask user] = Present to user and wait for response before continuing.
- [Decide] = Evaluate conditions and branch.
</Agent Annotations>

<Gotchas>
1. file_read_pdf extracts raw text without formatting. Tables and multi-column layouts may produce garbled text ordering. If the diff looks nonsensical, inform the user that PDF layout extraction may have affected accuracy.
2. file_read_docx returns Markdown-formatted text. Heading markers (##) and list prefixes (-) are part of the extracted content and should be treated as structural, not diffable text changes.
3. difflib.SequenceMatcher has O(n squared) worst-case performance. For documents over 10,000 lines, chunk into sections first and compare section-by-section.
4. Documents with entirely different structures (e.g., comparing a bullet-point doc against a prose doc) will produce noisy diffs. Detect this condition (over 80% of content flagged as changed) and warn the user.
</Gotchas>

<Instructions>

<Workflow - Compare
description="Load two documents, compute differences, generate summary and/or visual diff, and present results."
tools=[file_read_docx, file_read_pdf, file_read, run_python, file_write, open_in_session_tab]
triggers=["compare these docs", "what changed between versions", "diff these files", "document comparison", "show differences between"]
>

1. [Decide] Determine file types of {{file_a}} and {{file_b}} by extension.
   - .docx: use file_read_docx
   - .pdf: use file_read_pdf
   - .md, .txt, or other text: use file_read
   - Unsupported extension: [Ask user] "That file type isn't supported. I can compare DOCX, PDF, Markdown, and plain text files."

2. [Agent] Load both documents using the appropriate reader from step 1.
   Validate: Both files return non-empty text content.
   If fails: Report which file could not be read and the error. Ask user to confirm the path.

3. [Decide] Are documents identical?
   - Yes: Inform user: "These documents are identical. No differences found." Stop.
   - No: Continue.

4. [Decide] Are documents excessively large (either file over 50,000 characters)?
   - Yes: [Ask user] "These are large documents ([X] and [Y] characters). Comparison may take a moment. Want me to proceed with the full comparison, or compare a specific section range?"
   - No: Continue.

5. [Agent] Compute differences using run_python with difflib.SequenceMatcher.
   - Split documents into paragraphs (double newline or heading boundaries).
   - Compare at paragraph level to identify added, removed, modified, and moved sections.
   - For modified paragraphs, run word-level diff to identify inline changes.
   Validate: Diff data structure produced with at least one of: additions, deletions, modifications.
   If fails: Fall back to simple line-by-line comparison.

6. [Decide] Check diff noise level. Is over 80% of content flagged as changed?
   - Yes: [Ask user] "These documents have very different structures. Over 80% of the content differs. The comparison will be noisy. Want me to proceed anyway, or would a high-level summary be more useful?"
   - No: Continue.

7. [Decide] What output does the user want (based on {{output_format}})?
   - "markdown" or "both": Continue to step 8.
   - "html" only: Skip to step 9.

8. [Agent] Generate a structured change summary in Markdown. Write to workspace as comparison_summary.md.
   Format per <Template - Change Summary>. Present the summary to the user immediately.
   Validate: Summary file is written and contains at least the Overview and Key Changes sections.

9. [Decide] Does the user want HTML output?
   - {{output_format}} is "html" or "both": Continue to step 10.
   - "markdown" only: Skip to step 11.

10. [Agent] Generate an HTML visual diff with side-by-side layout. Use the html_design skill tokens for styling. Write to workspace as comparison_diff.html.
    Features: side-by-side panels, green highlights (additions), red highlights (deletions), yellow highlights (modifications), line numbers, jump-to-change navigation, summary stats header.
    Validate: HTML file written and contains diff content.

11. [Agent] Open the generated file(s) in session tabs using open_in_session_tab.
    - If both formats: open summary first, then HTML diff.
    - If single format: open that file.

</Workflow - Compare>

</Instructions>

<Templates>

<Template - Change Summary>
# Document Comparison Summary

**File A (baseline)**: [filename]
**File B (revised)**: [filename]
**Date**: [comparison date]

## Overview
- Sections added: X
- Sections removed: X
- Sections modified: X
- Overall change magnitude: [Minor / Moderate / Significant / Major]

## Key Changes
1. [Most significant change in plain language]
2. [Second most significant]
3. ...

## Detailed Changes

### Added
- [New content summary]

### Removed
- [Removed content summary]

### Modified
- [Section name]: [what changed]
</Template>

</Templates>
