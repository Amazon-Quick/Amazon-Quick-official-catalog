---
description: "The blueprint JSON shape that scripts/render_wireframe.py accepts."
last_updated: 2026-11-22
---
# Wireframe renderer contract

The renderer accepts this JSON shape:

```json
{
  "title": "Regional performance",
  "subtitle": "Manager view · Data through 2026-08-31",
  "width": 1400,
  "height": 900,
  "columns": 12,
  "theme": {
    "primary": "#2563EB",
    "background": "#F8FAFC",
    "surface": "#FFFFFF",
    "text": "#172033"
  },
  "zones": [
    {"id": "sales", "title": "Sales YTD", "kind": "kpi", "x": 1, "y": 1, "w": 4, "h": 1, "details": ["Placeholder: $1.2M", "vs target"]},
    {"id": "trend", "title": "Monthly sales", "kind": "line", "x": 1, "y": 2, "w": 8, "h": 4, "details": ["MONTH(Order Date)", "SUM(Sales)"]}
  ],
  "filters": ["Relative date", "Region"],
  "notes": ["Click a region to filter the trend", "Mock values are placeholders"]
}
```

Required top-level keys: `title`, `width`, `height`, `columns`, and `zones`. Optional: `subtitle`, `theme`, `filters`, and `notes`.

Each zone requires `id`, `title`, `kind`, `x`, `y`, `w`, and `h`. `kind` is free text of up to 40 characters, shown above the zone's title, such as `kpi`, `line`, `bar`, `map`, or `table`; the renderer doesn't check it against a list. Coordinates are one-based grid values. `x + w - 1` must not exceed `columns`; all dimensions must be positive. Zone IDs must be unique and rectangles must not overlap. Optional `details` is an array of short strings.

Theme values must be six-digit hex colors. The renderer validates structure, escapes all text, and produces one self-contained HTML page. Don't replace an existing wireframe file unless the user has authorized it. It does not validate WCAG contrast or Tableau feasibility; those remain design/build checks.
