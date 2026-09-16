"""
description: Parse confined LAS 2.0 unwrapped well logs, inventory curves, read null-aware arrays, resolve aliases, and normalize supported units using only the Python standard library.
last_updated: 2026-09-15
origin: original
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

DEFAULT_NULL_VALUE = -999.25
METRES_TO_FEET = 3.28084
MICROSECONDS_PER_METRE_TO_FOOT = 0.3048


class Operation(StrEnum):
    """Supported LAS reader operations."""

    READ_METADATA = "read_metadata"
    READ_CURVES = "read_curves"
    RESOLVE_ALIASES = "resolve_aliases"


class ErrorCode(StrEnum):
    """Machine-readable LAS reader failures."""

    DUPLICATE_CURVE = "DUPLICATE_CURVE"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    INVALID_INPUT = "INVALID_INPUT"
    MALFORMED_DATA = "MALFORMED_DATA"
    MALFORMED_LAS = "MALFORMED_LAS"
    MISSING_ASCII_SECTION = "MISSING_ASCII_SECTION"
    MISSING_CURVE_SECTION = "MISSING_CURVE_SECTION"
    MISSING_VERSION = "MISSING_VERSION"
    PARENT_TRAVERSAL = "PARENT_TRAVERSAL"
    PATH_OUTSIDE_WORKSPACE = "PATH_OUTSIDE_WORKSPACE"
    UNKNOWN_OPERATION = "UNKNOWN_OPERATION"
    UNSUPPORTED_LAS_VERSION = "UNSUPPORTED_LAS_VERSION"
    WORKSPACE_DIR_MISSING = "WORKSPACE_DIR_MISSING"
    WRAPPED_LAS_UNSUPPORTED = "WRAPPED_LAS_UNSUPPORTED"


class LasReaderError(ValueError):
    """A LAS request or parse failure with a stable error code."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class LasRequest:
    """Validated request envelope."""

    operation: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class HeaderItem:
    """One LAS section record."""

    mnemonic: str
    unit: str
    value: str
    description: str


@dataclass(frozen=True)
class CurveDefinition:
    """One curve declaration from the LAS curve section."""

    mnemonic: str
    unit: str
    description: str


@dataclass(frozen=True)
class LasDocument:
    """Parsed LAS metadata plus unparsed ASCII data rows."""

    version: str
    wrap: str
    well: tuple[HeaderItem, ...]
    curves: tuple[CurveDefinition, ...]
    null_value: float
    data_lines: tuple[str, ...]


class RequestParser:
    """Parse one inline JSON request envelope."""

    def __init__(self, request_json: str) -> None:
        self._request_json = request_json

    def parse(self) -> LasRequest:
        try:
            value = json.loads(self._request_json)
        except json.JSONDecodeError as error:
            raise LasReaderError(
                ErrorCode.INVALID_INPUT,
                f"request is not valid JSON: {error.msg}",
            ) from error
        if not isinstance(value, dict):
            raise LasReaderError(
                ErrorCode.INVALID_INPUT, "request root must be a JSON object"
            )
        operation = value.get("operation")
        arguments = value.get("arguments", {})
        if not isinstance(operation, str) or not operation:
            raise LasReaderError(
                ErrorCode.INVALID_INPUT,
                "request.operation must be a non-empty string",
            )
        if not isinstance(arguments, dict):
            raise LasReaderError(
                ErrorCode.INVALID_INPUT,
                "request.arguments must be a JSON object",
            )
        return LasRequest(operation=operation, arguments=arguments)


class WorkspacePathResolver:
    """Resolve a requested LAS path within WORKSPACE_DIR."""

    def __init__(self, workspace_dir: str | None, requested_path: str) -> None:
        self._workspace_dir = workspace_dir
        self._requested_path = requested_path

    def resolve(self) -> Path:
        if not self._workspace_dir:
            raise LasReaderError(
                ErrorCode.WORKSPACE_DIR_MISSING,
                "WORKSPACE_DIR is required for file operations",
            )
        requested = Path(self._requested_path)
        if ".." in requested.parts:
            raise LasReaderError(
                ErrorCode.PARENT_TRAVERSAL,
                "path must not contain parent traversal",
            )
        workspace = Path(self._workspace_dir).resolve()
        resolved = (
            requested.resolve()
            if requested.is_absolute()
            else (workspace / requested).resolve()
        )
        if resolved != workspace and workspace not in resolved.parents:
            raise LasReaderError(
                ErrorCode.PATH_OUTSIDE_WORKSPACE,
                "path must resolve within WORKSPACE_DIR",
            )
        if not resolved.is_file():
            raise LasReaderError(
                ErrorCode.FILE_NOT_FOUND,
                f"LAS file not found within WORKSPACE_DIR: {self._requested_path}",
            )
        return resolved


class LasTextReader:
    """Read one UTF-8 LAS file from disk."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> str:
        try:
            return self._path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise LasReaderError(
                ErrorCode.MALFORMED_LAS, "LAS file must be UTF-8 text"
            ) from error


class LasParser:
    """Parse LAS 2.0 section metadata without external packages."""

    def __init__(self, text: str) -> None:
        self._text = text

    def parse(self) -> LasDocument:
        section_items: dict[str, list[HeaderItem]] = {
            "VERSION": [],
            "WELL": [],
            "CURVE": [],
        }
        data_lines: list[str] = []
        current_section = ""
        found_ascii = False

        for raw_line in self._text.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("~"):
                section_name = stripped[1:].strip().upper()
                section_code = section_name[:1]
                current_section = {
                    "V": "VERSION",
                    "W": "WELL",
                    "C": "CURVE",
                    "A": "ASCII",
                }.get(section_code, "OTHER")
                if current_section == "ASCII":
                    found_ascii = True
                continue
            if current_section in section_items:
                section_items[current_section].append(self._parse_item(raw_line))
            elif current_section == "ASCII":
                data_lines.append(stripped)

        version_item = self._find_item(section_items["VERSION"], "VERS")
        if version_item is None:
            raise LasReaderError(
                ErrorCode.MISSING_VERSION, "LAS version section must define VERS"
            )
        version = version_item.value.strip()
        try:
            numeric_version = float(version)
        except ValueError as error:
            raise LasReaderError(
                ErrorCode.MALFORMED_LAS, f"LAS VERS is not numeric: {version}"
            ) from error
        if numeric_version != 2.0:
            raise LasReaderError(
                ErrorCode.UNSUPPORTED_LAS_VERSION,
                f"only LAS 2.0 is supported; found LAS {version}",
            )

        wrap_item = self._find_item(section_items["VERSION"], "WRAP")
        wrap = wrap_item.value.strip().upper() if wrap_item is not None else "NO"
        if wrap != "NO":
            raise LasReaderError(
                ErrorCode.WRAPPED_LAS_UNSUPPORTED,
                f"wrapped LAS data is unsupported; WRAP is {wrap or 'UNKNOWN'}",
            )
        if not found_ascii:
            raise LasReaderError(
                ErrorCode.MISSING_ASCII_SECTION,
                "LAS file is missing the ~A or ~ASCII data section",
            )
        if not section_items["CURVE"]:
            raise LasReaderError(
                ErrorCode.MISSING_CURVE_SECTION,
                "LAS file has no curve definitions",
            )

        curve_definitions = tuple(
            CurveDefinition(
                mnemonic=item.mnemonic,
                unit=item.unit,
                description=item.description,
            )
            for item in section_items["CURVE"]
        )
        mnemonics = [curve.mnemonic for curve in curve_definitions]
        if len(set(mnemonics)) != len(mnemonics):
            raise LasReaderError(
                ErrorCode.DUPLICATE_CURVE,
                "LAS curve mnemonics must be unique",
            )

        null_item = self._find_item(section_items["WELL"], "NULL")
        null_value = DEFAULT_NULL_VALUE
        if null_item is not None:
            try:
                null_value = float(null_item.value)
            except ValueError as error:
                raise LasReaderError(
                    ErrorCode.MALFORMED_LAS,
                    f"LAS NULL is not numeric: {null_item.value}",
                ) from error
            if not math.isfinite(null_value):
                raise LasReaderError(ErrorCode.MALFORMED_LAS, "LAS NULL must be finite")

        return LasDocument(
            version=version,
            wrap=wrap,
            well=tuple(section_items["WELL"]),
            curves=curve_definitions,
            null_value=null_value,
            data_lines=tuple(data_lines),
        )

    def _parse_item(self, raw_line: str) -> HeaderItem:
        content, separator, description = raw_line.partition(":")
        if "." not in content:
            raise LasReaderError(
                ErrorCode.MALFORMED_LAS,
                f"LAS section record is missing '.': {raw_line.strip()}",
            )
        mnemonic_text, remainder = content.split(".", 1)
        mnemonic = mnemonic_text.strip().upper()
        if not mnemonic:
            raise LasReaderError(
                ErrorCode.MALFORMED_LAS, "LAS section record has no mnemonic"
            )
        unit = ""
        value = ""
        if remainder and not remainder[0].isspace():
            parts = remainder.strip().split(None, 1)
            unit = parts[0].upper()
            value = parts[1].strip() if len(parts) == 2 else ""
        else:
            value = remainder.strip()
        return HeaderItem(
            mnemonic=mnemonic,
            unit=unit,
            value=value,
            description=description.strip() if separator else "",
        )

    def _find_item(self, items: list[HeaderItem], mnemonic: str) -> HeaderItem | None:
        return next((item for item in items if item.mnemonic == mnemonic), None)


class AliasResolver:
    """Resolve curve mnemonics to stable canonical names."""

    _ALIASES = {
        "GR": "GR",
        "SGR": "GR",
        "HSGR": "GR",
        "GRR": "GR",
        "GRN": "GR",
        "GRS": "GR",
        "GRD": "GR",
        "ECGR": "GR",
        "GRAM": "GR",
        "GR_ED": "GR",
        "GR_ARC": "GR",
        "NPHI": "NPHI",
        "HNPHI": "NPHI",
        "HTNP": "NPHI",
        "NPOR": "NPHI",
        "TNPH": "NPHI",
        "APLC": "NPHI",
        "CN": "NPHI",
        "BPHI": "NPHI",
        "NEU": "NPHI",
        "RHOB": "RHOB",
        "HRHOB": "RHOB",
        "RHOZ": "RHOB",
        "DEN": "RHOB",
        "DENS": "RHOB",
        "RT": "RT",
        "ILD": "RT",
        "HILD": "RT",
        "RILD": "RT",
        "RDEP": "RT",
        "LLD": "RT",
        "ILM": "RT",
        "HILM": "RT",
        "RILM": "RT",
        "LLM": "RT",
        "MSFL": "RT",
        "RXOZ": "RT",
        "RFOC": "RT",
        "DEPT": "DEPTH",
        "DEPTH": "DEPTH",
        "MD": "DEPTH",
        "DT": "DT",
        "HDT": "DT",
        "DTCO": "DT",
        "DTC": "DT",
        "DT4P": "DT",
        "AC": "DT",
        "SONIC": "DT",
        "CALI": "CALI",
        "HCALI": "CALI",
        "CAL": "CALI",
        "DRHO": "DRHO",
        "PEF": "PEF",
        "HPEF": "PEF",
        "PE": "PEF",
    }

    def __init__(self, mnemonics: list[str]) -> None:
        self._mnemonics = mnemonics

    def resolve(self) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        for mnemonic in self._mnemonics:
            normalized = mnemonic.strip().upper()
            canonical = self._ALIASES.get(normalized, normalized)
            resolved.append(
                {
                    "mnemonic": mnemonic,
                    "normalized_mnemonic": normalized,
                    "canonical_name": canonical,
                    "recognized": normalized in self._ALIASES,
                }
            )
        return resolved


class CurveReader:
    """Parse LAS ASCII rows into raw and canonical null-aware curve arrays."""

    def __init__(
        self,
        document: LasDocument,
        depth_min: float | None,
        depth_max: float | None,
    ) -> None:
        self._document = document
        self._depth_min = depth_min
        self._depth_max = depth_max

    def read(self) -> dict[str, Any]:
        if self._depth_min is not None and self._depth_max is not None:
            if self._depth_min > self._depth_max:
                raise LasReaderError(
                    ErrorCode.INVALID_INPUT,
                    "depth_min must be less than or equal to depth_max",
                )
        rows: list[list[float | None]] = []
        expected_columns = len(self._document.curves)
        for row_number, line in enumerate(self._document.data_lines, start=1):
            fields = line.split()
            if len(fields) != expected_columns:
                raise LasReaderError(
                    ErrorCode.MALFORMED_DATA,
                    f"ASCII row {row_number} has {len(fields)} values; expected {expected_columns}",
                )
            row: list[float | None] = []
            for field in fields:
                try:
                    value = float(field)
                except ValueError as error:
                    raise LasReaderError(
                        ErrorCode.MALFORMED_DATA,
                        f"ASCII row {row_number} contains a non-numeric value",
                    ) from error
                if not math.isfinite(value):
                    raise LasReaderError(
                        ErrorCode.MALFORMED_DATA,
                        f"ASCII row {row_number} contains a non-finite value",
                    )
                row.append(
                    None
                    if math.isclose(
                        value,
                        self._document.null_value,
                        rel_tol=0.0,
                        abs_tol=1e-9,
                    )
                    else value
                )
            depth = row[0]
            if depth is None:
                raise LasReaderError(
                    ErrorCode.MALFORMED_DATA,
                    f"ASCII row {row_number} has a null depth value",
                )
            if self._depth_min is not None and depth < self._depth_min:
                continue
            if self._depth_max is not None and depth > self._depth_max:
                continue
            rows.append(row)

        raw_curves = {
            curve.mnemonic: [row[index] for row in rows]
            for index, curve in enumerate(self._document.curves)
        }
        source_units = {curve.mnemonic: curve.unit for curve in self._document.curves}
        alias_records = AliasResolver(list(raw_curves)).resolve()
        canonical_curves: dict[str, list[float | None]] = {}
        canonical_units: dict[str, str] = {}
        canonical_sources: dict[str, str] = {}
        canonical_counts: dict[str, int] = {}
        for alias in alias_records:
            source_name = str(alias["normalized_mnemonic"])
            base_name = str(alias["canonical_name"])
            canonical_counts[base_name] = canonical_counts.get(base_name, 0) + 1
            suffix = canonical_counts[base_name]
            canonical_name = base_name if suffix == 1 else f"{base_name}_{suffix}"
            values, target_unit = self._convert_values(
                base_name,
                source_units[source_name],
                raw_curves[source_name],
            )
            canonical_curves[canonical_name] = values
            canonical_units[canonical_name] = target_unit
            canonical_sources[canonical_name] = source_name

        return {
            "status": "success",
            "operation": Operation.READ_CURVES.value,
            "sample_count": len(rows),
            "depth_mnemonic": self._document.curves[0].mnemonic,
            "depth_window": {
                "minimum": self._depth_min,
                "maximum": self._depth_max,
                "unit": self._document.curves[0].unit,
            },
            "null_value": self._document.null_value,
            "curves": raw_curves,
            "units": source_units,
            "canonical_curves": canonical_curves,
            "canonical_units": canonical_units,
            "canonical_sources": canonical_sources,
        }

    def _convert_values(
        self,
        canonical_name: str,
        source_unit: str,
        values: list[float | None],
    ) -> tuple[list[float | None], str]:
        unit = source_unit.strip().upper()
        factor = 1.0
        target_unit = unit
        if canonical_name == "DEPTH" and unit == "M":
            factor = METRES_TO_FEET
            target_unit = "FT"
        elif canonical_name == "DEPTH" and unit == "FT":
            target_unit = "FT"
        elif canonical_name == "NPHI" and unit in {"%", "PU"}:
            factor = 0.01
            target_unit = "V/V"
        elif canonical_name == "NPHI" and unit == "V/V":
            target_unit = "V/V"
        elif canonical_name in {"RHOB", "DRHO"} and unit == "G/C3":
            target_unit = "G/CC"
        elif canonical_name in {"RHOB", "DRHO"} and unit == "G/CC":
            target_unit = "G/CC"
        elif canonical_name == "DT" and unit == "US/M":
            factor = MICROSECONDS_PER_METRE_TO_FOOT
            target_unit = "US/FT"
        elif canonical_name == "DT" and unit == "US/FT":
            target_unit = "US/FT"
        elif canonical_name == "RT" and unit == "OHMM":
            target_unit = "OHMM"
        converted = [None if value is None else value * factor for value in values]
        return converted, target_unit


class LasOperationExecutor:
    """Execute one LAS request against injected text or alias arguments."""

    def __init__(self, request: LasRequest, workspace_dir: str | None) -> None:
        self._request = request
        self._workspace_dir = workspace_dir

    def execute(self) -> dict[str, Any]:
        try:
            operation = Operation(self._request.operation)
        except ValueError:
            return self._error(
                ErrorCode.UNKNOWN_OPERATION,
                f"unsupported operation: {self._request.operation}",
                supported_operations=[item.value for item in Operation],
            )
        try:
            if operation == Operation.RESOLVE_ALIASES:
                return self._resolve_aliases()
            path = self._resolve_path()
            document = LasParser(LasTextReader(path).read()).parse()
            if operation == Operation.READ_METADATA:
                return self._read_metadata(path, document)
            return self._read_curves(path, document)
        except LasReaderError as error:
            return self._error(error.code, str(error))
        except OSError as error:
            return self._error(ErrorCode.MALFORMED_LAS, str(error))

    def _resolve_aliases(self) -> dict[str, Any]:
        mnemonics = self._request.arguments.get("mnemonics")
        if not isinstance(mnemonics, list) or not mnemonics:
            raise LasReaderError(
                ErrorCode.INVALID_INPUT,
                "mnemonics must be a non-empty JSON array",
            )
        if any(not isinstance(item, str) or not item.strip() for item in mnemonics):
            raise LasReaderError(
                ErrorCode.INVALID_INPUT,
                "mnemonics must contain only non-empty strings",
            )
        aliases = AliasResolver(mnemonics).resolve()
        return {
            "status": "success",
            "operation": Operation.RESOLVE_ALIASES.value,
            "aliases": aliases,
            "mapping": {
                str(item["normalized_mnemonic"]): str(item["canonical_name"])
                for item in aliases
            },
        }

    def _resolve_path(self) -> Path:
        path_value = self._request.arguments.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            raise LasReaderError(
                ErrorCode.INVALID_INPUT,
                "path must be a non-empty string",
            )
        allowed_arguments = {
            Operation.READ_METADATA.value: {"path"},
            Operation.READ_CURVES.value: {"path", "depth_min", "depth_max"},
        }
        unexpected = sorted(
            set(self._request.arguments) - allowed_arguments[self._request.operation]
        )
        if unexpected:
            raise LasReaderError(
                ErrorCode.INVALID_INPUT,
                f"unexpected arguments for {self._request.operation}: {', '.join(unexpected)}",
            )
        return WorkspacePathResolver(self._workspace_dir, path_value).resolve()

    def _read_metadata(self, path: Path, document: LasDocument) -> dict[str, Any]:
        well = {
            item.mnemonic: {
                "unit": item.unit,
                "value": self._coerce_value(item.value),
                "description": item.description,
            }
            for item in document.well
        }
        curves = [
            {
                "mnemonic": curve.mnemonic,
                "unit": curve.unit,
                "description": curve.description,
                "null_value": document.null_value,
            }
            for curve in document.curves
        ]
        return {
            "status": "success",
            "operation": Operation.READ_METADATA.value,
            "source_path": str(path),
            "version": document.version,
            "wrap": document.wrap,
            "null_value": document.null_value,
            "well": well,
            "curve_count": len(curves),
            "curves": curves,
        }

    def _read_curves(self, path: Path, document: LasDocument) -> dict[str, Any]:
        depth_min = self._optional_finite_number("depth_min")
        depth_max = self._optional_finite_number("depth_max")
        result = CurveReader(document, depth_min, depth_max).read()
        result["source_path"] = str(path)
        return result

    def _optional_finite_number(self, name: str) -> float | None:
        value = self._request.arguments.get(name)
        if value is None:
            return None
        if isinstance(value, bool):
            raise LasReaderError(
                ErrorCode.INVALID_INPUT, f"{name} must be numeric, not boolean"
            )
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise LasReaderError(
                ErrorCode.INVALID_INPUT, f"{name} must be numeric"
            ) from error
        if not math.isfinite(number):
            raise LasReaderError(ErrorCode.INVALID_INPUT, f"{name} must be finite")
        return number

    def _coerce_value(self, value: str) -> str | float:
        try:
            number = float(value)
        except ValueError:
            return value
        return number if math.isfinite(number) else value

    def _error(self, code: ErrorCode, message: str, **extra: Any) -> dict[str, Any]:
        return {
            "status": "error",
            "code": code.value,
            "message": message,
            **extra,
        }


class JsonOutput:
    """Write one machine-readable JSON response."""

    def __init__(self, value: dict[str, Any]) -> None:
        self._value = value

    def write(self) -> None:
        print(json.dumps(self._value, indent=2, sort_keys=True))


class LasReaderCommand:
    """Parse, execute, and emit one LAS reader request."""

    def __init__(self, request_json: str, workspace_dir: str | None) -> None:
        self._request_json = request_json
        self._workspace_dir = workspace_dir

    def run(self) -> int:
        payload = json.loads(self._request_json)
        if self._workspace_dir and "workspace_dir" not in payload:
            payload["workspace_dir"] = self._workspace_dir
        result = run(payload)
        JsonOutput(result).write()
        return 0 if result.get("status") == "success" else 2


def run(request_object: dict[str, Any]) -> dict[str, Any]:
    """Execute one request object and return the result dict (sandbox entry point).

    ``workspace_dir`` may be supplied in the request object; it is required in
    the Amazon Quick sandbox because the process environment is read-only. When
    absent, the WORKSPACE_DIR environment variable is used.
    """
    workspace_dir = request_object.get("workspace_dir") or os.environ.get(
        "WORKSPACE_DIR"
    )
    payload = {k: v for k, v in request_object.items() if k != "workspace_dir"}
    try:
        request = RequestParser(json.dumps(payload)).parse()
        return LasOperationExecutor(request, workspace_dir).execute()
    except LasReaderError as error:
        return {"status": "error", "code": error.code.value, "message": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read confined LAS 2.0 unwrapped well logs from JSON requests."
    )
    parser.add_argument("--request-json", required=True, help="Inline JSON request.")
    arguments = parser.parse_args()
    return LasReaderCommand(
        request_json=arguments.request_json,
        workspace_dir=os.environ.get("WORKSPACE_DIR"),
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
