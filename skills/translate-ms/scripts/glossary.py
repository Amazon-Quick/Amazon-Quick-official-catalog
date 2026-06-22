"""
Phase 1 — Custom translation glossary handling.

Parses the user-editable glossary CSV (references/glossary.csv), matches source
and target language columns, and generates per-batch glossary instruction blocks
that are embedded in worker objectives. This ensures workers respect custom
terminology (brand names to preserve, domain-specific translations, etc.).

Also provides sanitize_batch_for_embedding() which serializes a batch list to
compact JSON for safe embedding in worker objective strings.

Self-contained — no cross-file dependencies.
"""

import csv
import json


def sanitize_batch_for_embedding(batch):
    """Serialize batch to ASCII-safe JSON string for embedding in worker objectives."""
    return json.dumps(batch, ensure_ascii=True)


def load_glossary_from_content(csv_content):
    """Parse glossary from CSV content string. Returns list of dicts or empty list."""
    if not csv_content or not csv_content.strip():
        return []
    return _load_glossary_from_text(csv_content)


def _load_glossary_from_text(csv_text):
    """Parse glossary CSV text, skipping lines above '# ---' delimiter."""
    lines = csv_text.strip().splitlines()

    data_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "# ---":
            data_start = i + 1
            break

    csv_data = "\n".join(lines[data_start:])
    reader = csv.DictReader(csv_data.splitlines())

    glossary = []
    for row in reader:
        lang_values = [v.strip() for k, v in row.items() if k != "match_type" and v]
        if not lang_values:
            continue
        glossary.append(row)

    if glossary:
        print(f"Glossary: loaded {len(glossary)} entries")
    return glossary


def match_glossary_columns(glossary, source_language, target_language):
    """Direct .lower() column match. Returns (glossary_source, glossary_target, all_headers)."""
    if not glossary:
        return "", "", []
    columns = [k for k in glossary[0].keys() if k.lower() != "match_type"]
    if not columns:
        return "", "", []

    source_lower = source_language.lower().strip()
    glossary_source = ""
    for col in columns:
        if col.lower() == source_lower:
            glossary_source = col
            break

    target_lower = target_language.lower().strip()
    glossary_target = ""
    for col in columns:
        if col.lower() == target_lower:
            glossary_target = col
            break

    if glossary_source and glossary_target:
        print(
            f"Custom translation glossary: matched source='{glossary_source}', target='{glossary_target}'"
        )
        return glossary_source, glossary_target, columns
    elif glossary_target:
        glossary_source = columns[0]
        print(
            f"Custom translation glossary: target='{glossary_target}', source defaulted to '{glossary_source}'"
        )
        return glossary_source, glossary_target, columns
    else:
        print(
            f"Custom translation glossary: no direct match for target '{target_language}' in columns {columns}"
        )
        return "", "", columns


def get_glossary_instruction(batch, glossary, glossary_source, glossary_target):
    """Build compact glossary instruction block for a worker prompt."""
    if not glossary_source or not glossary_target:
        return ""
    target_col = glossary_target.lower().strip()
    source_col = glossary_source.lower().strip()

    batch_text = " ".join(p["full_paragraph"] for p in batch).lower()

    matches = []
    for entry in glossary:
        source_term = entry.get(source_col, "").strip()
        target_term = entry.get(target_col, "").strip()
        match_type = entry.get("match_type", "exact").strip().lower()

        if not source_term or not target_term:
            continue

        if match_type == "fuzzy":
            stem = source_term.rstrip("aeiouy").lower()
            if len(stem) >= 3 and stem in batch_text:
                matches.append((source_term, target_term, match_type))
        else:
            if source_term.lower() in batch_text:
                matches.append((source_term, target_term, match_type))

    if not matches:
        return ""

    lines = ["GLOSSARY (use these exact translations — do not override):"]
    lines.append("source|target|type")
    for source, target, mtype in matches:
        lines.append(f"{source}|{target}|{mtype}")

    return "\n".join(lines)
