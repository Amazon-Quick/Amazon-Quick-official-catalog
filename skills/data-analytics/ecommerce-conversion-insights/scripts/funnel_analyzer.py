"""
description: Loads e-commerce funnel data from a CSV or Excel file and emits a standardized funnel structure as JSON.
last_updated: 2026-09-13
origin: original

Funnel Analyzer.

Loads funnel data from uploaded CSV or Excel files and returns
a standardized structure for analysis.

Usage:
    python funnel_analyzer.py --file-path PATH
                              --segments "device,geo,category"

Output:
    JSON to stdout with standardized funnel structure:
    {
        "stages": [...],
        "data": [...],
        "metadata": {...}
    }

Design:
    ColumnNormalizer (pure) maps source headers to canonical names.
    FunnelFileReader (I/O) loads the file into a DataFrame.
    FunnelStandardizer (pure over an in-memory DataFrame) builds the
    standardized result. FunnelAnalysis (facade) wires the reader to the
    standardizer. stdout carries only the machine-readable JSON that the
    downstream revenue calculator re-parses with json.load, so diagnostics
    and errors are written to stderr to keep that payload uncorrupted.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from enum import StrEnum

import pandas as pd
from pydantic import BaseModel


class _PrintStream:
    """Routes log records to stdout via print (the sandbox only returns stdout)."""

    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=_PrintStream(),
    force=True,
)
logger = logging.getLogger(__name__)


class CanonicalColumn(StrEnum):
    """Canonical funnel column names the analyzer standardizes to."""

    STAGE = "stage"
    VISITORS = "visitors"
    CONVERSIONS = "conversions"
    DEVICE = "device"
    GEO = "geo"
    CATEGORY = "category"
    AVG_ORDER_VALUE = "avg_order_value"


# Alias groups keyed by canonical column. Matching is case-insensitive on the
# stripped lowercase header; groups are disjoint, and the first match wins.
_COLUMN_ALIASES: dict[CanonicalColumn, tuple[str, ...]] = {
    CanonicalColumn.STAGE: ("stage_name", "stage", "funnel_stage", "step"),
    CanonicalColumn.VISITORS: ("visitors", "users", "sessions", "traffic"),
    CanonicalColumn.CONVERSIONS: ("conversions", "converted", "completed"),
    CanonicalColumn.DEVICE: (
        "device",
        "device_type",
        "devicecategory",
        "device_category",
    ),
    CanonicalColumn.GEO: ("geo", "geography", "country", "region"),
    CanonicalColumn.CATEGORY: ("category", "product_category", "item_category"),
    CanonicalColumn.AVG_ORDER_VALUE: ("avg_order_value", "aov", "order_value"),
}

_REQUIRED_COLUMNS: set[str] = {
    CanonicalColumn.STAGE.value,
    CanonicalColumn.VISITORS.value,
}
_DEFAULT_SEGMENTS: tuple[str, ...] = ("device", "geo", "category")
_CSV_SUFFIX: str = ".csv"
_EXCEL_SUFFIXES: tuple[str, ...] = (".xlsx", ".xls")
_SOURCE_LABEL: str = "uploaded_file"
_NOT_AVAILABLE: str = "N/A"


class ColumnMapping(BaseModel):
    """Maps source column names to canonical funnel column names."""

    mapping: dict[str, str]


class FunnelMetadata(BaseModel):
    """Provenance and shape metadata for a standardized funnel result."""

    source: str
    file_path: str
    date_range: dict
    segments: list[str]
    fetched_at: str
    row_count: int


class StandardizedFunnel(BaseModel):
    """The standardized funnel structure emitted as JSON.

    Records stay open dicts because the segment dimensions present vary per
    upload and their key order mirrors the requested segment order; a fixed
    model would reorder or add absent keys and change the output bytes.
    """

    stages: list
    data: list[dict]
    metadata: FunnelMetadata


class ColumnNormalizer:
    """Maps a list of source column names to canonical names (pure)."""

    def __init__(self, columns: list[str]) -> None:
        self.columns = columns

    def normalize(self) -> ColumnMapping:
        """Return the source-to-canonical rename mapping for matched columns."""
        mapping: dict[str, str] = {}
        for column in self.columns:
            column_lower = column.lower().strip()
            for canonical, aliases in _COLUMN_ALIASES.items():
                if column_lower in aliases:
                    mapping[column] = canonical.value
                    break
        return ColumnMapping(mapping=mapping)


class FunnelFileReader:
    """Reads a CSV or Excel funnel file into a DataFrame (I/O)."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def read(self) -> pd.DataFrame:
        """Load the funnel file, raising ValueError for unsupported formats."""
        if self.file_path.endswith(_CSV_SUFFIX):
            return pd.read_csv(self.file_path)
        if self.file_path.endswith(_EXCEL_SUFFIXES):
            return pd.read_excel(self.file_path)
        raise ValueError(
            f"Unsupported file format: {self.file_path}. Use .csv, .xlsx, or .xls"
        )


class FunnelStandardizer:
    """Turns a loaded funnel DataFrame into a StandardizedFunnel (pure)."""

    def __init__(
        self, frame: pd.DataFrame, segments: list[str], file_path: str
    ) -> None:
        self.frame = frame
        self.segments = segments
        self.file_path = file_path

    def standardize(self) -> StandardizedFunnel:
        """Normalize headers, validate required columns, and build the result."""
        mapping = ColumnNormalizer(list(self.frame.columns)).normalize().mapping
        frame = self.frame.rename(columns=mapping)

        missing = _REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(
                f"Missing required columns: {missing}. "
                f"Found columns: {list(frame.columns)}. "
                "Expected: stage_name/stage, visitors/users/sessions"
            )

        stage_names = frame["stage"].unique().tolist()
        records = self._build_records(frame, stage_names)

        return StandardizedFunnel(
            stages=stage_names,
            data=records,
            metadata=FunnelMetadata(
                source=_SOURCE_LABEL,
                file_path=self.file_path,
                date_range={"start": _NOT_AVAILABLE, "end": _NOT_AVAILABLE},
                segments=[s for s in self.segments if s in frame.columns],
                fetched_at=datetime.now().isoformat(),
                row_count=len(frame),
            ),
        )

    def _build_records(self, frame: pd.DataFrame, stage_names: list) -> list[dict]:
        """Build one standardized record dict per DataFrame row."""
        records: list[dict] = []
        for _, row in frame.iterrows():
            record: dict = {
                "stage": row["stage"],
                "stage_order": stage_names.index(row["stage"]) + 1,
                "visitors": int(row["visitors"]),
                "events": int(row.get("conversions", row["visitors"])),
            }
            for segment in self.segments:
                if segment in frame.columns:
                    record[segment] = str(row[segment])
            if CanonicalColumn.AVG_ORDER_VALUE.value in frame.columns:
                record["avg_order_value"] = float(row["avg_order_value"])
            records.append(record)
        return records


class FunnelAnalysis:
    """Facade: read a funnel file and return its standardized structure."""

    def __init__(self, file_path: str, segments: list[str]) -> None:
        self.file_path = file_path
        self.segments = segments

    def analyze(self) -> StandardizedFunnel:
        """Load the file and standardize it into the funnel structure."""
        frame = FunnelFileReader(self.file_path).read()
        return FunnelStandardizer(frame, self.segments, self.file_path).standardize()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Load and standardize funnel data from CSV or Excel files")
    )
    parser.add_argument(
        "--file-path",
        required=True,
        help="Path to CSV or Excel funnel data file",
    )
    parser.add_argument(
        "--segments",
        default=",".join(_DEFAULT_SEGMENTS),
        help="Comma-separated segment dimensions to extract",
    )
    return parser


def main() -> int:
    """Parse arguments, standardize the funnel file, and emit JSON to stdout."""
    args = _build_parser().parse_args()
    segments = [s.strip() for s in args.segments.split(",")]

    try:
        result = FunnelAnalysis(args.file_path, segments).analyze()
    except Exception as error:  # noqa: BLE001 - any failure becomes the error payload
        error_output = {
            "error": str(error),
            "troubleshooting": (
                "Verify file exists and contains required "
                "columns (stage_name, visitors). "
                "Supported formats: .csv, .xlsx, .xls"
            ),
        }
        sys.stderr.write(json.dumps(error_output, indent=2) + "\n")
        return 1

    sys.stdout.write(json.dumps(result.model_dump(), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
