"""
description: Profile an attached CSV or Excel extract for 02-datasets.md. Reads a CSV in bounded chunks and prints only a short summary: row count, distinct counts of the key columns, the date range of the time column, and the null rate of each column. Never prints row values.
last_updated: 2026-11-24
"""

from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from collections.abc import Iterable, Iterator
from enum import Enum
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict

DEFAULT_CHUNK_ROWS = 100_000
MAX_CHUNK_ROWS = 500_000
DISTINCT_CAP = 10_000
MAX_EXCEL_BYTES = 20_000_000
MAX_EXCEL_ROWS = 200_000
MAX_EXCEL_UNCOMPRESSED_BYTES = 200_000_000
MAX_CSV_BYTES = 1_000_000_000
MAX_VALUE_CHARS = 200
UNSAFE_CHARS = frozenset("|`<>#*[]")
MAX_LISTED_COLUMNS = 50
MAX_NAME_CHARS = 60


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


class ProfileInputError(ValueError):
    """The extract or the request can't be profiled; the message names no file content."""


class ExtractFormat(str, Enum):  # noqa: UP042 (str, Enum) keeps Python 3.10 support
    """The extract file types the profiler reads."""

    CSV = ".csv"
    XLSX = ".xlsx"


class ProfileRequest(BaseModel):
    """Which columns to profile as keys and as the time column."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key_columns: list[str]
    date_column: str | None = None


class ColumnProfile(BaseModel):
    """The null count and rate of one column."""

    name: str
    null_count: int
    null_rate: float


class KeyProfile(BaseModel):
    """The distinct count of one key column, capped at DISTINCT_CAP."""

    name: str
    distinct_count: int
    capped: bool


class ExtractProfile(BaseModel):
    """The summary of one extract."""

    row_count: int
    columns: list[ColumnProfile]
    keys: list[KeyProfile]
    date_column: str | None
    date_min: str | None
    date_max: str | None
    unparsed_dates: int


class ChunkProfiler:
    """Profiles already-loaded chunks of an extract. Pure: no file access."""

    def __init__(self, chunks: Iterable[pd.DataFrame], request: ProfileRequest) -> None:
        self.chunks = chunks
        self.request = request

    def profile(self) -> ExtractProfile:
        row_count = 0
        nulls: dict[str, int] = {}
        distinct: dict[str, set[str]] = {key: set() for key in self.request.key_columns}
        capped = dict.fromkeys(self.request.key_columns, False)
        date_min: pd.Timestamp | None = None
        date_max: pd.Timestamp | None = None
        unparsed = 0
        for chunk in self.chunks:
            self._check_columns(chunk)
            row_count += len(chunk)
            for name, count in chunk.isna().sum().items():
                nulls[str(name)] = nulls.get(str(name), 0) + int(count)
            for key in self.request.key_columns:
                capped[key] = (
                    self._add_distinct(distinct[key], chunk[key]) or capped[key]
                )
            if self.request.date_column is not None:
                raw = chunk[self.request.date_column]
                parsed = pd.to_datetime(raw, errors="coerce", format="mixed")
                unparsed += int((parsed.isna() & raw.notna()).sum())
                date_min = _earliest(date_min, parsed.min())
                date_max = _latest(date_max, parsed.max())
        return ExtractProfile(
            row_count=row_count,
            columns=[
                ColumnProfile(
                    name=name,
                    null_count=count,
                    null_rate=count / row_count if row_count else 0.0,
                )
                for name, count in nulls.items()
            ],
            keys=[
                KeyProfile(
                    name=key, distinct_count=len(distinct[key]), capped=capped[key]
                )
                for key in self.request.key_columns
            ],
            date_column=self.request.date_column,
            date_min=None if date_min is None else date_min.date().isoformat(),
            date_max=None if date_max is None else date_max.date().isoformat(),
            unparsed_dates=unparsed,
        )

    def _check_columns(self, chunk: pd.DataFrame) -> None:
        wanted = list(self.request.key_columns)
        if self.request.date_column is not None:
            wanted.append(self.request.date_column)
        missing = [name for name in wanted if name not in chunk.columns]
        if missing:
            available = ", ".join(
                _safe_name(c) for c in list(chunk.columns)[:MAX_LISTED_COLUMNS]
            )
            raise ProfileInputError(
                f"columns not in the extract: {', '.join(_safe_name(m) for m in missing)}. Available: {available}"
            )

    @staticmethod
    def _add_distinct(seen: set[str], values: pd.Series) -> bool:
        for value in values.dropna().astype(str).unique():
            if len(seen) >= DISTINCT_CAP:
                return True
            seen.add(value[:MAX_VALUE_CHARS])
        return False


class ProfileSummary:
    """Builds the short text summary of a profile."""

    def __init__(self, profile: ExtractProfile) -> None:
        self.profile = profile

    def build(self) -> str:
        profile = self.profile
        lines = [f"Rows: {profile.row_count:,}"]
        for key in profile.keys:
            marker = "+" if key.capped else ""
            lines.append(
                f"Distinct {_safe_name(key.name)}: {key.distinct_count:,}{marker}"
            )
        if profile.date_column is not None:
            lines.append(
                f"Date range of {_safe_name(profile.date_column)}: {profile.date_min or 'none parsed'}"
                f" to {profile.date_max or 'none parsed'} ({profile.unparsed_dates:,} values not read as dates)"
            )
        with_nulls = [column for column in profile.columns if column.null_count]
        lines.append(f"Columns: {len(profile.columns)}, {len(with_nulls)} with nulls")
        for column in with_nulls[:MAX_LISTED_COLUMNS]:
            lines.append(f"  {_safe_name(column.name)}: {column.null_rate:.1%} null")
        return "\n".join(lines)


class ExtractChunkReader:
    """Reads an extract from disk as a stream of string-typed chunks."""

    def __init__(self, path: Path, chunk_rows: int) -> None:
        self.path = path
        self.chunk_rows = chunk_rows

    def read(self) -> Iterator[pd.DataFrame]:
        extract_format = ExtractFormat(self.path.suffix.lower())
        size = self.path.stat().st_size
        if extract_format is ExtractFormat.CSV:
            if size > MAX_CSV_BYTES:
                raise ProfileInputError(
                    "CSV extract is larger than 1 GB; extract the reconciled period only"
                )
            yield from pd.read_csv(self.path, dtype=str, chunksize=self.chunk_rows)
            return
        if size > MAX_EXCEL_BYTES:
            raise ProfileInputError(
                "Excel extract is larger than 20 MB; save it as CSV"
            )
        if self._uncompressed_size() > MAX_EXCEL_UNCOMPRESSED_BYTES:
            raise ProfileInputError(
                "Excel extract expands to more than 200 MB; save it as CSV"
            )
        sheet = pd.read_excel(self.path, dtype=str, nrows=MAX_EXCEL_ROWS + 1)
        if len(sheet) > MAX_EXCEL_ROWS:
            raise ProfileInputError(
                "Excel extract has more than 200,000 rows; save it as CSV"
            )
        yield sheet

    def _uncompressed_size(self) -> int:
        try:
            with zipfile.ZipFile(self.path) as archive:
                return sum(member.file_size for member in archive.infolist())
        except zipfile.BadZipFile as error:
            raise ProfileInputError("the .xlsx file is not a valid workbook") from error


class ExtractProfileReport:
    """Reads the extract, profiles it and returns the summary text."""

    def __init__(self, path: Path, request: ProfileRequest, chunk_rows: int) -> None:
        self.path = path
        self.request = request
        self.chunk_rows = chunk_rows

    def build(self) -> str:
        chunks = ExtractChunkReader(self.path, self.chunk_rows).read()
        return ProfileSummary(ChunkProfiler(chunks, self.request).profile()).build()


def _earliest(
    current: pd.Timestamp | None, candidate: pd.Timestamp
) -> pd.Timestamp | None:
    if pd.isna(candidate):
        return current
    return candidate if current is None or candidate < current else current


def _latest(
    current: pd.Timestamp | None, candidate: pd.Timestamp
) -> pd.Timestamp | None:
    if pd.isna(candidate):
        return current
    return candidate if current is None or candidate > current else current


def _safe_name(name: object) -> str:
    """A column name is file content: keep it printable, plain and short."""
    text = "".join(
        ch if ch.isprintable() and ch not in UNSAFE_CHARS else "?" for ch in str(name)
    )
    return text[:MAX_NAME_CHARS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profile a CSV or Excel extract.")
    parser.add_argument("extract", help="Path to the .csv or .xlsx extract.")
    parser.add_argument(
        "--key", action="append", default=[], help="A key column. Repeat for each."
    )
    parser.add_argument("--date-column", default=None, help="The time column.")
    parser.add_argument(
        "--chunk-rows", type=int, default=DEFAULT_CHUNK_ROWS, help="Rows per CSV chunk."
    )
    args = parser.parse_args(argv)

    path = Path(args.extract)
    if not path.is_file():
        logger.error("Not found: %s", _safe_name(path.name))
        return 2
    if path.suffix.lower() not in {item.value for item in ExtractFormat}:
        logger.error(
            "Only .csv and .xlsx extracts are supported: %s", _safe_name(path.name)
        )
        return 2
    if not 1 <= args.chunk_rows <= MAX_CHUNK_ROWS:
        logger.error("--chunk-rows must be between 1 and %d", MAX_CHUNK_ROWS)
        return 2
    request = ProfileRequest(key_columns=args.key, date_column=args.date_column)
    try:
        summary = ExtractProfileReport(path, request, args.chunk_rows).build()
    except ProfileInputError as error:
        logger.error("Cannot profile %s: %s", _safe_name(path.name), error)
        return 2
    except (ValueError, OSError, pd.errors.ParserError) as error:
        # A reader's message can quote file content, so print only its type.
        logger.error(
            "Cannot profile %s: the file could not be read (%s)",
            _safe_name(path.name),
            type(error).__name__,
        )
        return 2
    logger.info("Extract profile\n%s", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
