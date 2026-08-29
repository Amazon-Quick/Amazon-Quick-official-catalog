"""
Markdown to DOCX converter.

Converts a markdown file to a properly formatted Word document using python-docx.
Handles headings, inline formatting (bold, italic, code, hyperlinks), lists (bulleted
and numbered with nesting), horizontal rules, blockquotes, tables, images, and
paragraph continuation.

Dependencies: python-docx, lxml, Pillow (all pre-installed in Amazon Quick sandbox).
"""

import os
import re

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from lxml import etree

# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def OxmlElement(tag):
    """Create an OxmlElement with the given tag."""
    nsmap = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "xml": "http://www.w3.org/XML/1998/namespace",
    }
    prefix, local = tag.split(":")
    uri = nsmap[prefix]
    return etree.SubElement(etree.Element("dummy"), f"{{{uri}}}{local}")


def make_element(tag):
    """Create a standalone lxml element with proper namespace."""
    nsmap = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "xml": "http://www.w3.org/XML/1998/namespace",
    }
    prefix, local = tag.split(":")
    uri = nsmap[prefix]
    return etree.Element(f"{{{uri}}}{local}", nsmap=nsmap)


# ---------------------------------------------------------------------------
# Hyperlink support
# ---------------------------------------------------------------------------


def add_hyperlink(paragraph, text, url):
    """Add a clickable hyperlink to a paragraph."""
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )

    w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    r_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    hyperlink = etree.SubElement(paragraph._p, f"{{{w_ns}}}hyperlink")
    hyperlink.set(f"{{{r_ns}}}id", r_id)

    run_elem = etree.SubElement(hyperlink, f"{{{w_ns}}}r")
    rPr = etree.SubElement(run_elem, f"{{{w_ns}}}rPr")

    color = etree.SubElement(rPr, f"{{{w_ns}}}color")
    color.set(f"{{{w_ns}}}val", "0563C1")

    u = etree.SubElement(rPr, f"{{{w_ns}}}u")
    u.set(f"{{{w_ns}}}val", "single")

    t_elem = etree.SubElement(run_elem, f"{{{w_ns}}}t")
    t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t_elem.text = text


# ---------------------------------------------------------------------------
# Horizontal rule
# ---------------------------------------------------------------------------


def add_horizontal_rule(doc):
    """Add a horizontal rule as a paragraph with a bottom border."""
    p = doc.add_paragraph()
    w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    pPr = p._p.find(f"{{{w_ns}}}pPr")
    if pPr is None:
        pPr = etree.SubElement(p._p, f"{{{w_ns}}}pPr")
        p._p.insert(0, pPr)

    pBdr = etree.SubElement(pPr, f"{{{w_ns}}}pBdr")
    bottom = etree.SubElement(pBdr, f"{{{w_ns}}}bottom")
    bottom.set(f"{{{w_ns}}}val", "single")
    bottom.set(f"{{{w_ns}}}sz", "6")
    bottom.set(f"{{{w_ns}}}space", "1")
    bottom.set(f"{{{w_ns}}}color", "auto")
    return p


# ---------------------------------------------------------------------------
# Inline formatting parser
# ---------------------------------------------------------------------------

INLINE_PATTERNS = [
    ("link", re.compile(r"\[([^\]]+)\]\(([^)]+)\)")),
    ("bold_italic", re.compile(r"\*\*\*(.+?)\*\*\*")),
    ("bold", re.compile(r"\*\*(.+?)\*\*")),
    ("italic", re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")),
    ("code", re.compile(r"`([^`]+)`")),
]


def parse_inline(text):
    segments = []
    _parse_inline_recursive(text, segments)
    return segments


def _parse_inline_recursive(text, segments):
    if not text:
        return
    earliest_match = None
    earliest_start = len(text)
    earliest_type = None
    for ptype, pattern in INLINE_PATTERNS:
        m = pattern.search(text)
        if m and m.start() < earliest_start:
            earliest_match = m
            earliest_start = m.start()
            earliest_type = ptype
    if earliest_match is None:
        segments.append(
            {"text": text, "bold": False, "italic": False, "code": False, "link": None}
        )
        return
    before = text[:earliest_start]
    if before:
        segments.append(
            {
                "text": before,
                "bold": False,
                "italic": False,
                "code": False,
                "link": None,
            }
        )
    if earliest_type == "link":
        segments.append(
            {
                "text": earliest_match.group(1),
                "bold": False,
                "italic": False,
                "code": False,
                "link": earliest_match.group(2),
            }
        )
    elif earliest_type == "bold_italic":
        segments.append(
            {
                "text": earliest_match.group(1),
                "bold": True,
                "italic": True,
                "code": False,
                "link": None,
            }
        )
    elif earliest_type == "bold":
        segments.append(
            {
                "text": earliest_match.group(1),
                "bold": True,
                "italic": False,
                "code": False,
                "link": None,
            }
        )
    elif earliest_type == "italic":
        segments.append(
            {
                "text": earliest_match.group(1),
                "bold": False,
                "italic": True,
                "code": False,
                "link": None,
            }
        )
    elif earliest_type == "code":
        segments.append(
            {
                "text": earliest_match.group(1),
                "bold": False,
                "italic": False,
                "code": True,
                "link": None,
            }
        )
    after = text[earliest_match.end() :]
    if after:
        _parse_inline_recursive(after, segments)


def apply_segments_to_paragraph(paragraph, segments):
    for seg in segments:
        if seg["link"]:
            add_hyperlink(paragraph, seg["text"], seg["link"])
        elif seg["code"]:
            run = paragraph.add_run(seg["text"])
            run.font.name = "Consolas"
            run.font.size = Pt(10)
        else:
            run = paragraph.add_run(seg["text"])
            if seg["bold"]:
                run.bold = True
            if seg["italic"]:
                run.italic = True


# ---------------------------------------------------------------------------
# Document style setup
# ---------------------------------------------------------------------------


def setup_styles(doc):
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)
    pf = style.paragraph_format
    pf.line_spacing = 1.15
    for level, (size, color_hex) in enumerate(
        [
            (24, "1F3864"),
            (18, "2E75B6"),
            (14, "2E75B6"),
            (12, "2E75B6"),
        ]
    ):
        style_name = f"Heading {level + 1}"
        try:
            h_style = doc.styles[style_name]
            h_style.font.name = "Calibri Light"
            h_style.font.size = Pt(size)
            h_style.font.bold = True
            r, g, b = (
                int(color_hex[0:2], 16),
                int(color_hex[2:4], 16),
                int(color_hex[4:6], 16),
            )
            h_style.font.color.rgb = RGBColor(r, g, b)
        except KeyError:
            pass


# ---------------------------------------------------------------------------
# Line classification
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
BULLET_RE = re.compile(r"^(\s*)([-*+])\s+(.+)$")
NUMBERED_RE = re.compile(r"^(\s*)(\d+)\.\s+(.+)$")
BLOCKQUOTE_RE = re.compile(r"^>\s*(.*)$")
HR_RE = re.compile(r"^(---+|\*\*\*+|___+)\s*$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s:]*[-]+[\s:]*")
IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")
CODE_FENCE_RE = re.compile(r"^```")


def classify_line(line):
    m = CODE_FENCE_RE.match(line)
    if m:
        return ("code_fence", line[3:].strip())
    m = HEADING_RE.match(line)
    if m:
        return ("heading", (len(m.group(1)), m.group(2).strip()))
    m = HR_RE.match(line)
    if m:
        return ("hr", None)
    m = IMAGE_RE.match(line)
    if m:
        return ("image", (m.group(1), m.group(2)))
    m = BLOCKQUOTE_RE.match(line)
    if m:
        return ("blockquote", m.group(1))
    m = TABLE_SEP_RE.match(line)
    if m:
        return ("table_sep", None)
    m = TABLE_ROW_RE.match(line)
    if m:
        return ("table_row", [c.strip() for c in m.group(1).split("|")])
    m = NUMBERED_RE.match(line)
    if m:
        return ("numbered", (len(m.group(1)), m.group(3)))
    m = BULLET_RE.match(line)
    if m:
        return ("bullet", (len(m.group(1)), m.group(3)))
    if line.strip() == "":
        return ("blank", None)
    return ("text", line)


# ---------------------------------------------------------------------------
# Main conversion function
# ---------------------------------------------------------------------------


def convert_markdown_to_docx(source_path, output_path, title=None):
    """
    Convert a markdown file to a formatted Word document.

    Args:
        source_path: Path to the .md file
        output_path: Path for the output .docx file
        title: Optional document title (overrides the first H1 if provided)

    Returns:
        Path to the generated .docx file
    """
    with open(source_path, encoding="utf-8") as f:
        lines = f.readlines()

    doc = Document()
    setup_styles(doc)

    in_code_block = False
    code_lines = []
    in_table = False
    table_rows = []
    paragraph_buffer = []
    source_dir = os.path.dirname(os.path.abspath(source_path))
    first_h1_seen = False

    def flush_paragraph_buffer():
        nonlocal paragraph_buffer
        if paragraph_buffer:
            combined = " ".join(paragraph_buffer)
            p = doc.add_paragraph()
            segments = parse_inline(combined)
            apply_segments_to_paragraph(p, segments)
            paragraph_buffer = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        data_rows = [
            r
            for r in table_rows
            if not all(set(cell.strip()) <= set("-: ") for cell in r)
        ]
        if not data_rows:
            in_table = False
            table_rows = []
            return
        num_cols = max(len(r) for r in data_rows)
        tbl = doc.add_table(rows=len(data_rows), cols=num_cols)
        tbl.style = "Table Grid"
        for i, row_cells in enumerate(data_rows):
            for j, cell_text in enumerate(row_cells):
                if j < num_cols:
                    cell = tbl.rows[i].cells[j]
                    cell.text = ""
                    p = cell.paragraphs[0]
                    segments = parse_inline(cell_text)
                    apply_segments_to_paragraph(p, segments)
        if len(data_rows) > 0:
            for cell in tbl.rows[0].cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.bold = True
        in_table = False
        table_rows = []

    def flush_code_block():
        nonlocal code_lines
        if code_lines:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            code_text = "\n".join(code_lines)
            run = p.add_run(code_text)
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            code_lines = []

    for line in lines:
        line = line.rstrip("\n")

        if in_code_block:
            if CODE_FENCE_RE.match(line):
                in_code_block = False
                flush_code_block()
            else:
                code_lines.append(line)
            continue

        line_type, data = classify_line(line)

        if line_type == "code_fence":
            flush_paragraph_buffer()
            if in_table:
                flush_table()
            in_code_block = True
            continue

        if line_type == "table_row":
            flush_paragraph_buffer()
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(data)
            continue
        elif line_type == "table_sep":
            if in_table:
                table_rows.append(["---"] * 10)
            continue
        elif in_table:
            flush_table()

        if line_type == "heading":
            flush_paragraph_buffer()
            level, text = data
            doc_level = min(level - 1, 3)
            if level == 1 and not first_h1_seen:
                first_h1_seen = True
                if title:
                    text = title
            p = doc.add_heading("", level=doc_level)
            segments = parse_inline(text)
            apply_segments_to_paragraph(p, segments)

        elif line_type == "hr":
            flush_paragraph_buffer()
            add_horizontal_rule(doc)

        elif line_type == "blockquote":
            flush_paragraph_buffer()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.5)
            w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            pPr = p._p.find(f"{{{w_ns}}}pPr")
            if pPr is None:
                pPr = etree.SubElement(p._p, f"{{{w_ns}}}pPr")
                p._p.insert(0, pPr)
            pBdr = etree.SubElement(pPr, f"{{{w_ns}}}pBdr")
            left = etree.SubElement(pBdr, f"{{{w_ns}}}left")
            left.set(f"{{{w_ns}}}val", "single")
            left.set(f"{{{w_ns}}}sz", "12")
            left.set(f"{{{w_ns}}}space", "4")
            left.set(f"{{{w_ns}}}color", "808080")
            if data:
                segments = parse_inline(data)
                apply_segments_to_paragraph(p, segments)
                for run in p.runs:
                    run.italic = True

        elif line_type == "bullet":
            flush_paragraph_buffer()
            indent, text = data
            style_name = "List Bullet 2" if indent >= 4 else "List Bullet"
            try:
                p = doc.add_paragraph(style=style_name)
            except KeyError:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(
                    0.25 + (0.25 if indent >= 4 else 0)
                )
            segments = parse_inline(text)
            apply_segments_to_paragraph(p, segments)

        elif line_type == "numbered":
            flush_paragraph_buffer()
            indent, text = data
            style_name = "List Number 2" if indent >= 4 else "List Number"
            try:
                p = doc.add_paragraph(style=style_name)
            except KeyError:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(
                    0.25 + (0.25 if indent >= 4 else 0)
                )
            segments = parse_inline(text)
            apply_segments_to_paragraph(p, segments)

        elif line_type == "image":
            flush_paragraph_buffer()
            alt, img_path = data
            if not os.path.isabs(img_path):
                img_path = os.path.join(source_dir, img_path)
            if os.path.exists(img_path):
                try:
                    doc.add_picture(img_path, width=Inches(5))
                except Exception:
                    p = doc.add_paragraph()
                    run = p.add_run(f"[Image: {alt or img_path}]")
                    run.italic = True
            else:
                p = doc.add_paragraph()
                run = p.add_run(f"[Image not found: {alt or img_path}]")
                run.italic = True

        elif line_type == "blank":
            flush_paragraph_buffer()

        elif line_type == "text":
            paragraph_buffer.append(data)

    flush_paragraph_buffer()
    if in_table:
        flush_table()
    if in_code_block:
        flush_code_block()

    doc.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python convert.py <input.md> <output.docx> [title]")
        sys.exit(1)
    src = sys.argv[1]
    out = sys.argv[2]
    t = sys.argv[3] if len(sys.argv) > 3 else None
    result = convert_markdown_to_docx(src, out, t)
    print(f"Converted: {result}")
