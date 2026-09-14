"""
description: Parses the user-editable glossary CSV and generates per-batch glossary instruction blocks so translation workers respect custom terminology.
last_updated: 2026-09-13
origin: original

Phase 1, Custom translation glossary handling.

Parses the user-editable glossary CSV (references/glossary.csv), matches source
and target language columns, and generates per-batch glossary instruction blocks
that are embedded in worker objectives. This ensures workers respect custom
terminology (brand names to preserve, domain-specific translations, etc.).

Also provides sanitize_batch_for_embedding() which serializes a batch list to
compact JSON for safe embedding in worker objective strings.

Self-contained, no cross-file dependencies.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from dataclasses import dataclass
from enum import StrEnum


class _PrintStream:
    """Stdout adapter so logging records reach the real stdout via print()."""

    def write(self, message: str) -> int:
        if message:
            print(message, end="", file=sys.__stdout__)
        return len(message)

    def flush(self) -> None:
        return None


logging.basicConfig(
    stream=_PrintStream(),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    force=True,
)

_LOGGER = logging.getLogger(__name__)


_GLOSSARY_DATA_DELIMITER = "# ---"
_MATCH_TYPE_KEY = "match_type"
_DEFAULT_MATCH_TYPE = "exact"
_FUZZY_STEM_STRIP_CHARS = "aeiouy"
_FUZZY_STEM_MIN_LENGTH = 3


class MatchType(StrEnum):
    """Supported glossary match strategies."""

    EXACT = "exact"
    FUZZY = "fuzzy"


@dataclass(frozen=True)
class _GlossaryMatch:
    """A single glossary term matched within a batch of text."""

    source: str
    target: str
    match_type: str


class _BatchSerializer:
    """Serialize a batch list to an ASCII-safe JSON string."""

    def serialize(self, batch: list) -> str:
        """Serialize batch to ASCII-safe JSON string for embedding in worker objectives."""
        return json.dumps(batch, ensure_ascii=True)


class _GlossaryLoader:
    """Parse glossary CSV content into a list of row dicts."""

    def __init__(
        self,
        data_delimiter: str = _GLOSSARY_DATA_DELIMITER,
        match_type_key: str = _MATCH_TYPE_KEY,
    ) -> None:
        self._data_delimiter = data_delimiter
        self._match_type_key = match_type_key

    def load(self, csv_content: str) -> list:
        """Parse glossary from CSV content string. Returns list of dicts or empty list."""
        if not csv_content or not csv_content.strip():
            return []
        return self._parse_text(csv_content)

    def _parse_text(self, csv_text: str) -> list:
        """Parse glossary CSV text, skipping lines above '# ---' delimiter."""
        lines = csv_text.strip().splitlines()

        data_start = 0
        for i, line in enumerate(lines):
            if line.strip() == self._data_delimiter:
                data_start = i + 1
                break

        csv_data = "\n".join(lines[data_start:])
        reader = csv.DictReader(csv_data.splitlines())

        glossary = []
        for row in reader:
            lang_values = [
                v.strip() for k, v in row.items() if k != self._match_type_key and v
            ]
            if not lang_values:
                continue
            glossary.append(row)

        if glossary:
            _LOGGER.info(f"Glossary: loaded {len(glossary)} entries")
        return glossary


class _GlossaryColumnMatcher:
    """Match source and target language columns against glossary headers."""

    def __init__(self, match_type_key: str = _MATCH_TYPE_KEY) -> None:
        self._match_type_key = match_type_key

    def match(
        self, glossary: list, source_language: str, target_language: str
    ) -> tuple:
        """Direct .lower() column match. Returns (glossary_source, glossary_target, all_headers)."""
        if not glossary:
            return "", "", []
        columns = [k for k in glossary[0].keys() if k.lower() != self._match_type_key]
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
            _LOGGER.info(
                f"Custom translation glossary: matched source='{glossary_source}', target='{glossary_target}'"
            )
            return glossary_source, glossary_target, columns
        elif glossary_target:
            glossary_source = columns[0]
            _LOGGER.info(
                f"Custom translation glossary: target='{glossary_target}', source defaulted to '{glossary_source}'"
            )
            return glossary_source, glossary_target, columns
        else:
            _LOGGER.info(
                f"Custom translation glossary: no direct match for target '{target_language}' in columns {columns}"
            )
            return "", "", columns


class _GlossaryInstructionBuilder:
    """Build a compact glossary instruction block for a worker prompt."""

    def __init__(
        self,
        default_match_type: str = _DEFAULT_MATCH_TYPE,
        fuzzy_stem_strip_chars: str = _FUZZY_STEM_STRIP_CHARS,
        fuzzy_stem_min_length: int = _FUZZY_STEM_MIN_LENGTH,
        match_type_key: str = _MATCH_TYPE_KEY,
    ) -> None:
        self._default_match_type = default_match_type
        self._fuzzy_stem_strip_chars = fuzzy_stem_strip_chars
        self._fuzzy_stem_min_length = fuzzy_stem_min_length
        self._match_type_key = match_type_key

    def build(
        self,
        batch: list,
        glossary: list,
        glossary_source: str,
        glossary_target: str,
    ) -> str:
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
            match_type = (
                entry.get(self._match_type_key, self._default_match_type)
                .strip()
                .lower()
            )

            if not source_term or not target_term:
                continue

            if match_type == MatchType.FUZZY.value:
                stem = source_term.rstrip(self._fuzzy_stem_strip_chars).lower()
                if len(stem) >= self._fuzzy_stem_min_length and stem in batch_text:
                    matches.append(_GlossaryMatch(source_term, target_term, match_type))
            else:
                if source_term.lower() in batch_text:
                    matches.append(_GlossaryMatch(source_term, target_term, match_type))

        if not matches:
            return ""

        lines = ["GLOSSARY (use these exact translations, do not override):"]
        lines.append("source|target|type")
        for match in matches:
            lines.append(f"{match.source}|{match.target}|{match.match_type}")

        return "\n".join(lines)


def sanitize_batch_for_embedding(batch: list) -> str:
    """Serialize batch to ASCII-safe JSON string for embedding in worker objectives."""
    return _BatchSerializer().serialize(batch)


def load_glossary_from_content(csv_content: str) -> list:
    """Parse glossary from CSV content string. Returns list of dicts or empty list."""
    return _GlossaryLoader().load(csv_content)


def match_glossary_columns(
    glossary: list, source_language: str, target_language: str
) -> tuple:
    """Direct .lower() column match. Returns (glossary_source, glossary_target, all_headers)."""
    return _GlossaryColumnMatcher().match(glossary, source_language, target_language)


def get_glossary_instruction(
    batch: list, glossary: list, glossary_source: str, glossary_target: str
) -> str:
    """Build compact glossary instruction block for a worker prompt."""
    return _GlossaryInstructionBuilder().build(
        batch, glossary, glossary_source, glossary_target
    )
