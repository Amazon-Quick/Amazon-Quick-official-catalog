"""
description: Text-level helpers for editing workbook XML parts: attributes, open tags, escaping, and a prefix-free view of a prefixed worksheet.
last_updated: 2026-11-24
"""

from __future__ import annotations

import re

CELL_ANY = re.compile(r"<c\b[^>]*?(?:/>|>.*?</c>)", re.S)


XML_MARKUP = re.compile(
    r"""<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<[^>"']*(?:(?:"[^"]*"|'[^']*')[^>"']*)*>""",
    re.S,
)


XML_NAME = re.compile(r"<(/?)([A-Za-z_][\w.:-]*)")


SHEET_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def map_element_names(xml, transform):
    """Change element names without touching attributes, text, comments or CDATA."""

    def replace(match):
        token = match.group(0)
        name = XML_NAME.match(token)
        if not name:
            return token
        return (
            token[: name.start(2)]
            + transform(name.group(2), token)
            + token[name.end(2) :]
        )

    return XML_MARKUP.sub(replace, xml)


def protect_xml_literals(xml):
    """Hide non-element markup from the editors, then restore its exact bytes."""
    literals = {}

    def protect(match):
        token = match.group(0)
        if XML_NAME.match(token):
            return token
        index = len(literals)
        marker = f"<!--sheet-review-preserved-{index}-->"
        while marker in xml or marker in literals:
            index += 1
            marker = f"<!--sheet-review-preserved-{index}-->"
        literals[marker] = token
        return marker

    return XML_MARKUP.sub(protect, xml), literals


def worksheet_view(xml):
    """Give the existing editors a prefix-free view of a uniformly prefixed sheet.

    Keep foreign prefixed extensions intact. Reject namespace layouts that cannot
    be restored without ambiguity instead of risking a change to their meaning.
    """
    root = next(
        (m.group(0) for m in XML_MARKUP.finditer(xml) if XML_NAME.match(m.group(0))),
        "",
    )
    name = XML_NAME.match(root)
    if not name or ":" not in name.group(2):
        return xml, ""
    prefix, local = name.group(2).split(":", 1)
    prefix += ":"
    if local != "worksheet":
        raise ValueError("Unsupported worksheet namespace; no changes applied")
    declaration = re.compile(
        rf"""\sxmlns:{re.escape(prefix[:-1])}\s*=\s*["']([^"']*)["']"""
    )
    bound = declaration.search(root)
    if not bound or bound.group(1) != SHEET_NAMESPACE:
        raise ValueError("Unsupported worksheet namespace; no changes applied")

    def strip(name, token):
        if any(m.group(1) != SHEET_NAMESPACE for m in declaration.finditer(token)):
            raise ValueError("Rebound worksheet namespace; no changes applied")
        if ":" not in name:
            raise ValueError("Mixed worksheet namespace prefixes; no changes applied")
        return name[len(prefix) :] if name.startswith(prefix) else name

    return map_element_names(xml, strip), prefix


CF_BLOCK = re.compile(
    r"<conditionalFormatting\b[^>]*>.*?</conditionalFormatting>", re.S
)


def cf_signature(block: str) -> str:
    """A highlight block's rule markup without its range and priority, so copies compare equal."""
    tag = open_tag(block)
    return re.sub(
        r'\spriority="[^"]*"', "", set_attr(tag, "sqref", None) + block[len(tag) :]
    )


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def cell_pat(coord):
    return re.compile(rf'<c\b(?=[^>]*?\sr="{coord}")[^>]*?(?:/>|>.*?</c>)', re.S)


def attr(tag: str, name: str):
    m = re.search(rf'\s{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def set_attr(tag: str, name: str, value):
    if value is None:
        return re.sub(rf'\s{name}="[^"]*"', "", tag)
    if re.search(rf'\s{name}="[^"]*"', tag):
        return re.sub(rf'(\s{name}=)"[^"]*"', rf'\g<1>"{value}"', tag)
    return re.sub(r"(/?>)$", rf' {name}="{value}"\1', tag, count=1)


def open_tag(el: str) -> str:
    return re.match(r"<[^>]*?/?>", el, re.S).group(0)
