#!/usr/bin/env python3
"""
description: Validate a dashboard blueprint JSON file and render it as a self-contained HTML wireframe.
last_updated: 2026-11-22

Validate a dashboard blueprint JSON file and render a self-contained HTML wireframe."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

TOP_KEYS = {
    "title",
    "subtitle",
    "width",
    "height",
    "columns",
    "theme",
    "zones",
    "filters",
    "notes",
}
ZONE_KEYS = {"id", "title", "kind", "x", "y", "w", "h", "details"}
THEME_KEYS = {"primary", "background", "surface", "text"}
DEFAULT_THEME = {
    "primary": "#2563EB",
    "background": "#F8FAFC",
    "surface": "#FFFFFF",
    "text": "#172033",
}
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class SpecError(ValueError):
    """Raised when the wireframe contract is violated."""


def text_value(value: Any, label: str, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{label} must be a non-empty string")
    value = value.strip()
    if len(value) > maximum:
        raise SpecError(f"{label} exceeds {maximum} characters")
    return value


def int_value(value: Any, label: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise SpecError(f"{label} must be an integer from {minimum} to {maximum}")
    return value


def string_list(value: Any, label: str, maximum_items: int = 12) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum_items:
        raise SpecError(f"{label} must be an array of at most {maximum_items} strings")
    return [text_value(item, f"{label}[{index}]") for index, item in enumerate(value)]


def validate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SpecError("input must be a JSON object")
    missing = {"title", "width", "height", "columns", "zones"} - set(payload)
    extra = set(payload) - TOP_KEYS
    if missing:
        raise SpecError(f"missing top-level keys: {sorted(missing)}")
    if extra:
        raise SpecError(f"unknown top-level keys: {sorted(extra)}")

    width = int_value(payload["width"], "width", 320, 3840)
    height = int_value(payload["height"], "height", 320, 2160)
    columns = int_value(payload["columns"], "columns", 1, 24)
    zones_raw = payload["zones"]
    if not isinstance(zones_raw, list) or not zones_raw or len(zones_raw) > 30:
        raise SpecError("zones must be an array containing 1 to 30 objects")

    zones, ids, cells = [], set(), set()
    for index, zone in enumerate(zones_raw):
        if not isinstance(zone, dict):
            raise SpecError(f"zones[{index}] must be an object")
        missing_zone = {"id", "title", "kind", "x", "y", "w", "h"} - set(zone)
        extra_zone = set(zone) - ZONE_KEYS
        if missing_zone:
            raise SpecError(f"zones[{index}] missing keys: {sorted(missing_zone)}")
        if extra_zone:
            raise SpecError(f"zones[{index}] has unknown keys: {sorted(extra_zone)}")
        zone_id = text_value(zone["id"], f"zones[{index}].id", 64)
        if zone_id in ids:
            raise SpecError(f"duplicate zone id: {zone_id}")
        ids.add(zone_id)
        x = int_value(zone["x"], f"zones[{index}].x", 1, columns)
        y = int_value(zone["y"], f"zones[{index}].y", 1, 50)
        w = int_value(zone["w"], f"zones[{index}].w", 1, columns)
        h = int_value(zone["h"], f"zones[{index}].h", 1, 50)
        if x + w - 1 > columns:
            raise SpecError(f"zones[{index}] exceeds the {columns}-column grid")
        occupied = {
            (column, row) for column in range(x, x + w) for row in range(y, y + h)
        }
        if cells & occupied:
            raise SpecError(f"zones[{index}] overlaps another zone")
        cells |= occupied
        zones.append(
            {
                "id": zone_id,
                "title": text_value(zone["title"], f"zones[{index}].title"),
                "kind": text_value(zone["kind"], f"zones[{index}].kind", 40),
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "details": string_list(
                    zone.get("details", []), f"zones[{index}].details", 8
                ),
            }
        )

    theme_raw = payload.get("theme", {})
    if not isinstance(theme_raw, dict) or set(theme_raw) - THEME_KEYS:
        raise SpecError(f"theme supports only: {sorted(THEME_KEYS)}")
    theme = {**DEFAULT_THEME, **theme_raw}
    for key, value in theme.items():
        if not isinstance(value, str) or not HEX.fullmatch(value):
            raise SpecError(f"theme.{key} must be a six-digit hex color")

    subtitle = payload.get("subtitle", "")
    if subtitle:
        subtitle = text_value(subtitle, "subtitle")
    return {
        "title": text_value(payload["title"], "title"),
        "subtitle": subtitle,
        "width": width,
        "height": height,
        "columns": columns,
        "theme": theme,
        "zones": zones,
        "filters": string_list(payload.get("filters", []), "filters"),
        "notes": string_list(payload.get("notes", []), "notes"),
    }


def render(spec: dict[str, Any]) -> str:
    esc = html.escape
    theme = spec["theme"]
    zone_html = []
    for zone in spec["zones"]:
        details = "".join(f"<li>{esc(item)}</li>" for item in zone["details"])
        zone_html.append(
            f'<section class="zone" style="grid-column:{zone["x"]}/span {zone["w"]};grid-row:{zone["y"]}/span {zone["h"]}" '
            f'aria-label="{esc(zone["title"], quote=True)}">'
            f'<div class="kind">{esc(zone["kind"])}</div><h2>{esc(zone["title"])}</h2><ul>{details}</ul></section>'
        )
    filters = "".join(f"<span>{esc(item)}</span>" for item in spec["filters"])
    notes = "".join(f"<li>{esc(item)}</li>" for item in spec["notes"])
    subtitle = (
        f'<p class="subtitle">{esc(spec["subtitle"])}</p>' if spec["subtitle"] else ""
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(spec["title"])} — wireframe</title>
<style>
:root{{--primary:{theme["primary"]};--bg:{theme["background"]};--surface:{theme["surface"]};--text:{theme["text"]}}}
*{{box-sizing:border-box}} body{{margin:0;background:#E5E7EB;color:var(--text);font:16px/1.4 system-ui,sans-serif}}
.frame{{width:min(calc(100vw - 32px),{spec["width"]}px);min-height:{spec["height"]}px;margin:16px auto;padding:20px;background:var(--bg);box-shadow:0 8px 28px #0002}}
header{{display:flex;align-items:end;justify-content:space-between;gap:20px;border-bottom:3px solid var(--primary);padding-bottom:12px}} h1{{font-size:24px;margin:0}} .subtitle{{margin:4px 0 0;color:var(--text);opacity:.72}}
.filters{{display:flex;flex-wrap:wrap;gap:8px}} .filters span{{background:#FFF7CC;border:1px solid #A16207;border-radius:6px;padding:6px 10px}}
.grid{{display:grid;grid-template-columns:repeat({spec["columns"]},minmax(0,1fr));grid-auto-rows:minmax(76px,auto);gap:12px;margin-top:16px}}
.zone{{min-width:0;background:var(--surface);border:1px solid #94A3B8;border-top:5px solid var(--primary);border-radius:8px;padding:14px;overflow:hidden}} .zone h2{{font-size:17px;margin:4px 0 10px}} .zone ul{{margin:0;padding-left:20px}} .kind{{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--primary)}}
footer{{margin-top:16px;border-top:1px solid #94A3B8;padding-top:10px}} footer h2{{font-size:14px;margin:0 0 6px}} footer ul{{margin:0;padding-left:20px}}
@media(max-width:760px){{.frame{{width:100%;margin:0;box-shadow:none}} header{{align-items:start;flex-direction:column}} .grid{{display:block}} .zone{{margin-top:12px}}}}
</style></head><body><main class="frame"><header><div><h1>{esc(spec["title"])}</h1>{subtitle}</div><nav class="filters" aria-label="Proposed filters">{filters}</nav></header>
<div class="grid">{"".join(zone_html)}</div><footer><h2>Blueprint notes</h2><ul>{notes}</ul></footer></main></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="wireframe JSON specification")
    parser.add_argument("output", type=Path, help="HTML output path")
    parser.add_argument(
        "--force", action="store_true", help="replace an existing output file"
    )
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as handle:
            spec = validate(json.load(handle))
        if not args.output.parent.is_dir():
            raise SpecError(f"output directory does not exist: {args.output.parent}")
        if args.input.resolve() == args.output.resolve():
            raise SpecError("input and output paths must differ")
        if args.output.exists() and not args.force:
            raise SpecError(
                "output already exists; use --force only after confirming replacement"
            )
        args.output.write_text(render(spec), encoding="utf-8")
    except (OSError, json.JSONDecodeError, SpecError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
