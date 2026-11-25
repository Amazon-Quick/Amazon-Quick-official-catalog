---
name: tableau-viz-critique
display_name: "Tableau Viz Critique (Preview)"
author: "Salesforce, Inc."
icon: assets/icon.svg
created_date: "2026-11-21"
last_updated: "2026-11-22"
description: Review and score Tableau dashboards or views from a render plus available Tableau metadata, using an evidence-based seven-domain rubric and prioritized recommendations. Use for critique or scoring; do not use to edit workbooks, validate underlying data accuracy, or assess business performance.
id: "eae6e66b-f7f9-477c-8724-a46f0b94974a"
checksum: "sha256:c306e3176547effc4150cb575f9acd53f56a0b38d1831fe264a86b08298d2d47"
---

# Tableau Viz Critique

Evaluate the visualization first and advise second. Ground every score in visible evidence, distinguish observation from inference, and keep review work read-only.

## Resolve the target

Accept any of these inputs:

- an attached screenshot or render;
- a Tableau view or workbook URL;
- a Tableau content name or canonical identifier;
- a workbook with a user-specified view to review.

When a Tableau MCP server is available, discover its actual search/list, metadata, and view-image capabilities before calling them. Resolve names and URLs to the canonical identifier returned by the server; do not assume a numeric route segment is an API identifier. Use only read operations.

Tool names here are the Tableau MCP server's own names. The host may list them with a server prefix (e.g. `mcp__<server>__get-view-image`); call the listed tool whose name ends in the name given here.

For a workbook with several relevant views, use the view the user named. If none was named and the choice would change the review, ask which view to score; otherwise state the selected view and why it is representative. Review every view only when the user requests workbook-wide coverage.

Metadata may establish owner, project, device layout, view names, or intended audience, but it is not evidence for a visual quality that is absent from the render.

## Show the dashboard

When the target is Tableau content, always show the dashboard to the user in the response before the review. Follow [`references/rendering.md`](references/rendering.md) for the render path, its fallback order, direct-URL construction, PNG download, and failure handling. Reuse the view LUID and URL already resolved for the review. A screenshot the user supplied is already visible, so don't render or show it again.

Start the reply with the dashboard: the direct link, then the image itself as a Markdown image, `![<view name>](workspace/downloads/<file name>)`. Quick displays it only when the path starts with `workspace/`. Naming the view doesn't show it.

If every render path fails, handle it as rendering.md's failure handling describes, then continue the review from whatever image you can inspect.

## Capture a render to score

Scoring needs an image you can inspect. An interactive render shows the user the dashboard but doesn't give you pixels, so also fetch a static PNG:

- If the render path already ended with the `get-view-image` fallback, score that PNG. Don't fetch another.
- Otherwise call `get-view-image` once with `viewId`, `format: "PNG"`, and the largest practical `width`/`height` that preserves the dashboard's aspect ratio. Handle the result exactly as [rendering.md](references/rendering.md#download-the-png-immediately) describes: pick the file name before calling, download a `resource_link` as the very next action with Quick's Download file tool, and retry once if the URL expires.
- Verify the file is a non-empty image, then inspect it with the available image-viewing tool.
- If the image is Tableau's sign-in page, the view is a data app, which Tableau's image renderer can't draw. Don't score it, retry, or show it. Give the user the direct link and ask for a screenshot of the app instead.
- Show the user the image you scored, before the score: show it inline in the reply as a Markdown image, as above. A link or file path alone doesn't count. Skip this only when that image is already visible in the chat: an inline image returned by the tool, a PNG already shown by rendering.md's fallback, or a screenshot the user supplied.

Do not conclude that a render is inaccessible merely because a browser blocks the image-host domain. Browser access and direct retrieval of an MCP-returned resource are separate paths; exhaust the connector's supported resource-delivery path first. Only ask the user for a screenshot after the PNG is unavailable or fails.

If the render is too small, clipped, blank, or stale enough to make scoring unreliable, request a better image instead of guessing. A screenshot supplied directly by the user does not require Tableau access.

## Establish context

Before scoring, identify:

- the dominant genre: business dashboard, analytical/exploratory, narrative, editorial, expressive/data art, or scientific/technical;
- the likely audience and time budget when supported by the request or artifact;
- the primary question the visualization appears to answer.

State the primary question in the review. Mark it **unclear** when the evidence does not support one. Do not penalize a narrative, analytical, or expressive visualization for lacking dashboard conventions that do not serve its genre.

## Score from evidence

Read [rubric.md](references/rubric.md) before assigning scores. Catalog meaningful strengths before gaps, but do not use a predetermined passing floor. Score each domain from 0–10 against its anchor descriptions and cite observable evidence for both high scores and material deductions.

Assess visible interactivity cues—filters, controls, navigation, selection state, and disclosure model—inside Audience Adaptation and Layout. Do not claim tooltip quality, action responsiveness, keyboard support, screen-reader structure, or parameter behavior from a static render.

Record the seven base scores, documented adjustments, and applicable caps in a JSON assessment. Read [assessment-schema.md](references/assessment-schema.md) for the required shape and adjustment identifiers.

The assessment and the scoring helper's result are internal scratch data, not user deliverables. Keep them in memory in Code Execution: don't write them to files, don't create them with an artifact-producing file-edit tool, and don't attach, open, link, render, mention, or otherwise surface them to the user. This doesn't apply to the downloaded render, which the user sees. Return only the formatted review unless the user explicitly requests JSON.

Score with the bundled helper, which does the deterministic weighting, validation, half-even rounding, safety status, and tier assignment. Run it in Code Execution, where the skill's scripts are importable by name; Run python on device can't import them. Code Execution runs Python, not a shell, and blocks `subprocess` and changes to `sys.path`, so don't run `scripts/score_viz.py` as a command or add its folder to the path. Build the assessment as a Python dict and pass it to `score_viz.calculate()`. It returns the result the script would print, and raises `ValueError` naming the problem when the assessment doesn't match the schema:

```python
import json
import score_viz

assessment = {"domains": {}, "caps": {}}  # fill in the shape from assessment-schema.md
try:
    result = score_viz.calculate(assessment)
except ValueError as exc:
    print("invalid assessment:", exc)  # fix the assessment and call again
else:
    print(json.dumps(result, indent=2, sort_keys=True))
```

If Code Execution is unavailable, apply the weights, caps, half-even rounding, and tiers from [rubric.md](references/rubric.md) manually and label the overall score `manually calculated`.

The helper is the arithmetic authority, not the visual evaluator. Never manufacture an adjustment merely to reach a tier. When it returns `safety_status: blocked`, display `Safety remediation required` instead of a quality tier and lead with the blocking issue.

If any domain genuinely cannot be assessed, do not invent a value or calculate an overall score. Deliver the supported qualitative findings, mark the missing domain, and request the evidence needed for a complete score.

## Deliver the review

Default to a complete but compact inline review unless the user requested a brief answer or a file. Do not delay useful findings behind a mandatory format question.

Include, in this order:

1. the dashboard: its direct link, then the PNG you scored as a Markdown image (`![<view name>](workspace/downloads/<file name>)`), unless that image is already visible in the chat (see [Show the dashboard](#show-the-dashboard));
2. final score, tier, genre, and primary question;
3. a short verdict;
4. the seven-domain scorecard with concrete evidence;
5. the main score drivers and any cap;
6. two to four prioritized recommendations.

For each recommendation, describe the current issue, the proposed change, the affected domain, and a coarse effort level such as Low, Medium, or High. Give numeric uplift or time estimates only when the evidence supports them; otherwise avoid false precision.

Read [report-guide.md](references/report-guide.md) when the user requests a detailed review, multiple views, or a document artifact. If a `.docx`, Google Doc, or another format is requested, use the appropriate available document capability and preserve the same evidence and score.

Keep humor light and never use it when discussing misleading presentation, accessibility barriers, or exposed sensitive data.

## Boundaries

- Review-only requests do not authorize workbook edits, publishing, comments, subscriptions, or other Tableau mutations.
- Route an authorized workbook repair to a workbook-authoring skill when available; do not silently change scope.
- Visual design review does not validate source data, calculation correctness, business conclusions, or performance unless the user supplies separate evidence and requests that analysis.
- Treat visible personal or sensitive data as evidence to minimize in the report, not content to reproduce.
- When only a static image is available, label interaction and accessibility limitations explicitly.
