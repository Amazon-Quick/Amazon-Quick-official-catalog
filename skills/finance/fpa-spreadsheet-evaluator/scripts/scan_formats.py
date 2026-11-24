"""
description: Cell style and number-format helpers for the workbook scan: color families, decimals, scale, display width and number-like text.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import colorsys
import re


def color_family(color) -> str:
    """Collapse a font/fill color to a family name so near-identical shades compare equal."""
    if color is None:
        return "auto"
    t = getattr(color, "type", None)
    if t == "theme":
        return "auto" if color.theme in (1, None) else f"theme{color.theme}"
    if t == "indexed":
        return "auto" if color.indexed in (8, 64, None) else f"indexed{color.indexed}"
    rgb = getattr(color, "rgb", None)
    if not isinstance(rgb, str) or len(rgb) < 6:
        return "auto"
    rgb = rgb[-6:].upper()
    r, g, b = (int(rgb[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < 0.25:
        return "auto"  # black and near-black read as the default text color
    if s < 0.15:
        return "white" if v > 0.9 else "gray"
    deg = h * 360
    for limit, name in (
        (15, "red"),
        (40, "orange"),
        (70, "yellow"),
        (170, "green"),
        (260, "blue"),
        (345, "purple"),
    ):
        if deg < limit:
            return name
    return "red"


def fill_family(fill) -> str:
    if fill is None or fill.fill_type in (None, "none"):
        return "none"
    fam = color_family(fill.fgColor)
    return "none" if fam in ("white",) else fam


COLOR_WORDS = {
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "black",
    "gray",
    "grey",
}


def fmt_section(fmt: str) -> str:
    return re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", (fmt or "General").split(";")[0])


def fmt_decimals(fmt: str):
    sec = fmt_section(fmt)
    if sec.strip().lower() == "general" or not re.search(r"[0#?]", sec):
        return None
    m = re.search(r"\.([0#?]+)", sec)
    return len(m.group(1)) if m else 0


def fmt_scale(fmt: str) -> str:
    raw = (fmt or "").split(";")[0]
    lit = " ".join(re.findall(r'"([^"]*)"', raw)).strip().upper()
    if re.search(r"\bMM\b|\bM\b", lit):
        return "millions"
    if re.search(r"\bK\b", lit):
        return "thousands"
    if re.search(r"\bB\b|\bBN\b", lit):
        return "billions"
    sec = fmt_section(raw)
    m = re.search(r"[0#?](,+)(?![0#?])", sec)
    n = len(m.group(1)) if m else 0
    return {0: "units", 1: "thousands", 2: "millions", 3: "billions"}.get(n, "units")


def display_text(value: float, fmt: str):
    """Rough text Excel would show for a number, to judge if it fits the column."""
    dec = fmt_decimals(fmt)
    if dec is None:
        return None
    sec = fmt_section(fmt)
    scale = {"units": 1, "thousands": 1e3, "millions": 1e6, "billions": 1e9}[
        fmt_scale(fmt)
    ]
    v = value * (100 if "%" in sec else 1) / scale
    sep = "," if re.search(r"[0#],[0#]", sec) else ""
    text = f"{abs(v):{sep}.{dec}f}"
    extra = sum(len(x) for x in re.findall(r'"([^"]*)"', fmt.split(";")[0]))
    extra += (
        sec.count("$")
        + sec.count("%")
        + (2 if value < 0 and "(" in fmt else 1 if value < 0 else 0)
    )
    return text, len(text) + extra


DATE_TEXT = re.compile(
    r"^\s*(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4}|[A-Za-z]{3}[- ]\d{1,2},? \d{4})\s*$"
)
NUM_TEXT = re.compile(r"^[-+(]?\$?\s*\d[\d,]*(\.\d+)?\s*%?\)?$")


def numeric_text(text):
    """Bound number recognition after a single linear whitespace trim."""
    text = text.strip()
    return len(text) <= 40 and bool(NUM_TEXT.fullmatch(text))


def plural(n, word, many=None) -> str:
    """'1 cell', '3 cells' - no '(s)' in what people read."""
    return f"{n:,} {word if n == 1 else (many or word + 's')}"


def is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)
