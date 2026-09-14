---
description: "Maps every supported markdown element to its Word equivalent with the python-docx code that implements each transformation."
last_updated: 2026-09-13
origin: original
---

# Element Mapping: Markdown to Word

This document maps every supported markdown element to its Word equivalent, including the python-docx code that implements each transformation.

## Headings

| Markdown | Word Style | Level |
|----------|-----------|-------|
| `# Title` | Title (Heading level 0) | `doc.add_heading(text, level=0)` |
| `## Heading` | Heading 1 | `doc.add_heading(text, level=1)` |
| `### Heading` | Heading 2 | `doc.add_heading(text, level=2)` |
| `#### Heading` | Heading 3 | `doc.add_heading(text, level=3)` |

Note: H1 maps to level=0 (Title style in Word). This is intentional: Word's Title style is visually distinct and serves as the document title.

## Inline Formatting

### Bold

```markdown
**bold text**
```

```python
run = paragraph.add_run("bold text")
run.bold = True
```

### Italic

```markdown
*italic text*
```

```python
run = paragraph.add_run("italic text")
run.italic = True
```

### Bold Italic

```markdown
***bold and italic***
```

```python
run = paragraph.add_run("bold and italic")
run.bold = True
run.italic = True
```

### Inline Code

```markdown
`code_here`
```

```python
run = paragraph.add_run("code_here")
run.font.name = 'Consolas'
run.font.size = Pt(10)
```

### Hyperlinks

```markdown
[display text](https://example.com)
```

```python
def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(
        url,
        'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',
        is_external=True
    )
    w_ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    r_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

    hyperlink = etree.SubElement(paragraph._p, f'{{{w_ns}}}hyperlink')
    hyperlink.set(f'{{{r_ns}}}id', r_id)

    run_elem = etree.SubElement(hyperlink, f'{{{w_ns}}}r')
    rPr = etree.SubElement(run_elem, f'{{{w_ns}}}rPr')

    color = etree.SubElement(rPr, f'{{{w_ns}}}color')
    color.set(f'{{{w_ns}}}val', '0563C1')

    u = etree.SubElement(rPr, f'{{{w_ns}}}u')
    u.set(f'{{{w_ns}}}val', 'single')

    t_elem = etree.SubElement(run_elem, f'{{{w_ns}}}t')
    t_elem.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t_elem.text = text
```

Result: Blue (#0563C1) underlined text that opens the URL when clicked in Word.

## Lists

### Bulleted List

```markdown
- First item
- Second item
```

```python
p = doc.add_paragraph(style='List Bullet')
# apply inline formatting to text
```

### Nested Bulleted List

```markdown
- Top level
    - Nested item
```

```python
# indent >= 4 spaces triggers nested style
p = doc.add_paragraph(style='List Bullet 2')
```

### Numbered List

```markdown
1. First item
2. Second item
```

```python
p = doc.add_paragraph(style='List Number')
```

### Nested Numbered List

```markdown
1. Top level
    1. Nested item
```

```python
p = doc.add_paragraph(style='List Number 2')
```

## Block Elements

### Horizontal Rule

```markdown
---
```

```python
def add_horizontal_rule(doc):
    p = doc.add_paragraph()
    w_ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    pPr = p._p.find(f'{{{w_ns}}}pPr')
    if pPr is None:
        pPr = etree.SubElement(p._p, f'{{{w_ns}}}pPr')
        p._p.insert(0, pPr)
    pBdr = etree.SubElement(pPr, f'{{{w_ns}}}pBdr')
    bottom = etree.SubElement(pBdr, f'{{{w_ns}}}bottom')
    bottom.set(f'{{{w_ns}}}val', 'single')
    bottom.set(f'{{{w_ns}}}sz', '6')
    bottom.set(f'{{{w_ns}}}space', '1')
    bottom.set(f'{{{w_ns}}}color', 'auto')
```

Also triggered by `***` and `___`.

### Blockquote

```markdown
> Quoted text goes here
```

```python
p = doc.add_paragraph()
p.paragraph_format.left_indent = Inches(0.5)
# Add gray left border via XML:
pBdr = etree.SubElement(pPr, f'{{{w_ns}}}pBdr')
left = etree.SubElement(pBdr, f'{{{w_ns}}}left')
left.set(f'{{{w_ns}}}val', 'single')
left.set(f'{{{w_ns}}}sz', '12')
left.set(f'{{{w_ns}}}space', '4')
left.set(f'{{{w_ns}}}color', '808080')
# Text rendered in italic
```

### Code Block

````markdown
```python
def hello():
    print("world")
```
````

```python
p = doc.add_paragraph()
p.paragraph_format.left_indent = Inches(0.25)
run = p.add_run(code_text)
run.font.name = 'Consolas'
run.font.size = Pt(9)
```

### Table

```markdown
| Column A | Column B |
|----------|----------|
| Cell 1   | Cell 2   |
```

```python
tbl = doc.add_table(rows=num_rows, cols=num_cols)
tbl.style = 'Table Grid'
# Header row cells get bold formatting
# Each cell's text has inline formatting applied
```

### Image

```markdown
![Alt text](path/to/image.png)
```

```python
if os.path.exists(img_path):
    doc.add_picture(img_path, width=Inches(5))
else:
    # Insert placeholder: [Image not found: path/to/image.png]
```

## Paragraph Continuation

Multiple consecutive non-blank lines that are not headings, lists, blockquotes, or other block elements are joined with a space and rendered as a single paragraph. A blank line starts a new paragraph.

```markdown
This is the first sentence.
This continues the same paragraph.

This starts a new paragraph.
```

Result: Two paragraphs. The first contains "This is the first sentence. This continues the same paragraph." The second contains "This starts a new paragraph."

## Style Configuration

The converter sets these defaults on document creation:

| Style | Font | Size | Weight | Color |
|-------|------|------|--------|-------|
| Normal | Calibri | 11pt | Regular | Black |
| Heading 1 | Calibri Light | 24pt | Bold | #1F3864 |
| Heading 2 | Calibri Light | 18pt | Bold | #2E75B6 |
| Heading 3 | Calibri Light | 14pt | Bold | #2E75B6 |
| Heading 4 | Calibri Light | 12pt | Bold | #2E75B6 |
| Inline Code | Consolas | 10pt | Regular | Black |
| Code Block | Consolas | 9pt | Regular | Black |

Line spacing for Normal paragraphs: 1.15.
