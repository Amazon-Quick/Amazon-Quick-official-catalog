"""
description: Parse confined LAS 2.0 well logs, resolve vendor aliases, validate required curves, and persist JSON output.
last_updated: 2026-09-16
origin: original
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WELL_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_DATA_ROOT = "automated-log-analysis-data"
DEFAULT_NULL_VALUE = -999.25
REQUIRED_CURVES = ("GR", "RHOB", "RT")
STANDARD_CURVES = {
    "BIT",
    "CALI",
    "DEPTH",
    "DT",
    "DTS",
    "GR",
    "NPHI",
    "PE",
    "PHID",
    "PHIE",
    "RHOB",
    "RSHL",
    "RT",
    "SP",
    "SW",
    "VSH",
}
CURVE_ALIASES = {
    "AHT10": "RSHL",
    "AHT90": "RT",
    "AT10": "RSHL",
    "AT90": "RT",
    "BPHI": "NPHI",
    "BS": "BIT",
    "BITSZ": "BIT",
    "C1": "CALI",
    "C2": "CALI",
    "CAL": "CALI",
    "CGR": "GR",
    "CNC": "NPHI",
    "CNCF": "NPHI",
    "DCAL": "CALI",
    "DEPT": "DEPTH",
    "DEN": "RHOB",
    "DENB": "RHOB",
    "DT4P": "DT",
    "DT4S": "DTS",
    "DTC": "DT",
    "DTCO": "DT",
    "DTSM": "DTS",
    "ECGR": "GR",
    "EDRHOB": "RHOB",
    "GR:1": "GR",
    "GRD": "GR",
    "GRR": "GR",
    "GRMA": "GR",
    "GR_ARC": "GR",
    "GR_EDTC": "GR",
    "HDRS": "RT",
    "HGR": "GR",
    "HNPHI": "NPHI",
    "HRHOB": "RHOB",
    "HCAL": "CALI",
    "ILD": "RT",
    "ILM": "RSHL",
    "LLD": "RT",
    "LLS": "RSHL",
    "M2R9": "RT",
    "NEU": "NPHI",
    "NPOR": "NPHI",
    "P40H": "RT",
    "PEF": "PE",
    "PEFZ": "PE",
    "PHIN": "NPHI",
    "RD": "RT",
    "RESD": "RT",
    "RESS": "RSHL",
    "RFOC": "RSHL",
    "RILD": "RT",
    "RILM": "RT",
    "RLA1": "RSHL",
    "RLA4": "RT",
    "RLA5": "RT",
    "RLLD": "RT",
    "RLLS": "RSHL",
    "ROBB": "RHOB",
    "RPCEHM": "RT",
    "RSHL_ARC": "RSHL",
    "RT_ARC": "RT",
    "SGR": "GR",
    "SPNT": "SP",
    "SSP": "SP",
    "TNPH": "NPHI",
    "TNPB": "NPHI",
    "VCL": "VSH",
    "VSHALE": "VSH",
    "VSH_GR": "VSH",
    "ZDEN": "RHOB",
    "RHOZ": "RHOB",
}
TEXT_MNEMONICS = {
    "API",
    "COMP",
    "CNTY",
    "CTRY",
    "DATE",
    "FLD",
    "LATI",
    "LIC",
    "LOC",
    "LONG",
    "PROV",
    "SRVC",
    "STAT",
    "UWI",
    "WELL",
    "WN",
}


class _PrintStream:
    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO, format="%(message)s", stream=_PrintStream(), force=True
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeaderItem:
    mnemonic: str
    unit: str
    value: str
    description: str


@dataclass(frozen=True)
class CurveDefinition:
    mnemonic: str
    unit: str
    description: str
    standard_name: str


@dataclass(frozen=True)
class ParsedLas:
    version: str
    wrap: bool
    well_info: dict[str, dict[str, Any] | Any]
    curves: tuple[CurveDefinition, ...]
    data_arrays: dict[str, list[float | None]]
    warnings: tuple[str, ...]


class WorkspacePathResolver:
    """Resolve one relative path beneath an explicit workspace directory."""

    def __init__(self, workspace_dir: str, relative_path: str, label: str) -> None:
        self._workspace_dir = workspace_dir
        self._relative_path = relative_path
        self._label = label

    def resolve(self) -> Path:
        if not self._workspace_dir:
            raise ValueError("workspace_dir is required")
        requested = Path(self._relative_path)
        if requested.is_absolute():
            raise ValueError(f"{self._label} must be relative to workspace_dir")
        if ".." in requested.parts:
            raise ValueError(f"{self._label} must not contain parent traversal")
        workspace = Path(self._workspace_dir).resolve()
        resolved = (workspace / requested).resolve()
        if resolved != workspace and workspace not in resolved.parents:
            raise ValueError(f"{self._label} escapes workspace_dir")
        return resolved


class AliasTableBuilder:
    """Merge optional caller-provided aliases over embedded defaults."""

    def __init__(self, aliases: dict[str, Any] | None) -> None:
        self._aliases = aliases

    def build(self) -> dict[str, str]:
        merged = dict(CURVE_ALIASES)
        if self._aliases is None:
            return merged
        if not isinstance(self._aliases, dict):
            raise ValueError("aliases must be a JSON object")
        for key, value in self._flatten(self._aliases).items():
            merged[key.upper()] = value.upper()
        return merged

    def _flatten(self, aliases: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in aliases.items():
            if isinstance(value, dict):
                result.update(self._flatten(value))
            elif isinstance(value, str):
                result[str(key)] = value
            else:
                raise ValueError("alias values must be strings or nested objects")
        return result


class LasParser:
    """Parse LAS 2.0 text into JSON-safe canonical arrays."""

    def __init__(self, text: str, aliases: dict[str, str]) -> None:
        self._text = text
        self._aliases = aliases

    def parse(self) -> ParsedLas:
        sections: dict[str, list[str]] = {}
        current = ""
        for raw_line in (
            self._text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        ):
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith("~"):
                current = stripped[1:].strip().upper()[:1]
                sections.setdefault(current, [])
                continue
            if current:
                sections.setdefault(current, []).append(raw_line)

        version = "2.0"
        wrap = False
        for line in sections.get("V", []):
            item = self._parse_header_line(line)
            if item is None:
                continue
            if item.mnemonic == "VERS":
                version = item.value or item.unit or "2.0"
            elif item.mnemonic == "WRAP":
                # "WRAP. YES" has no unit; a lone non-numeric token lands in unit.
                wrap = (item.value or item.unit).strip().upper() == "YES"
        if float(version) != 2.0:
            raise ValueError(f"only LAS 2.0 is supported; found LAS {version}")

        well_info: dict[str, dict[str, Any] | Any] = {}
        for line in sections.get("W", []):
            item = self._parse_header_line(line)
            if item is None:
                continue
            value = item.value
            unit = item.unit
            if item.mnemonic in TEXT_MNEMONICS:
                value = f"{unit} {value}".strip() or item.description
                unit = ""
            well_info[item.mnemonic] = {
                "value": value,
                "unit": unit,
                "description": item.description,
            }
        null_value = self._well_number(well_info, "NULL", DEFAULT_NULL_VALUE)
        well_name = self._well_text(well_info, ("WELL", "WN"))
        well_info["_well_name"] = well_name
        well_info["_null"] = null_value

        warnings: list[str] = []
        curves = self._parse_curves(sections.get("C", []), warnings)
        if not curves:
            raise ValueError("No curves found in ~C section")
        values = self._parse_values(sections.get("A", []), len(curves), warnings)
        sample_count = len(values) // len(curves)
        arrays: dict[str, list[float | None]] = {
            curve.standard_name: [] for curve in curves
        }
        for row_index in range(sample_count):
            start = row_index * len(curves)
            row = values[start : start + len(curves)]
            for column, curve in enumerate(curves):
                value = row[column]
                arrays[curve.standard_name].append(
                    None if math.isclose(value, null_value, abs_tol=0.01) else value
                )
        return ParsedLas(
            version=version,
            wrap=wrap,
            well_info=well_info,
            curves=tuple(curves),
            data_arrays=arrays,
            warnings=tuple(warnings),
        )

    def _parse_curves(
        self, lines: list[str], warnings: list[str]
    ) -> list[CurveDefinition]:
        curves: list[CurveDefinition] = []
        seen: dict[str, int] = {}
        for line in lines:
            item = self._parse_header_line(line)
            if item is None:
                continue
            standard = self._resolve_alias(item.mnemonic)
            duplicate_index = seen.get(standard, 0)
            seen[standard] = duplicate_index + 1
            unique_name = (
                standard if duplicate_index == 0 else f"{standard}_{duplicate_index}"
            )
            if duplicate_index:
                warnings.append(
                    f"Duplicate curve '{standard}' from '{item.mnemonic}'; renamed to '{unique_name}'"
                )
            curves.append(
                CurveDefinition(
                    mnemonic=item.mnemonic,
                    unit=item.unit,
                    description=item.description,
                    standard_name=unique_name,
                )
            )
        return curves

    def _resolve_alias(self, mnemonic: str) -> str:
        clean = mnemonic.strip().upper()
        clean_base = re.sub(r":\d+$", "", clean)
        if clean in STANDARD_CURVES:
            return clean
        return self._aliases.get(clean, self._aliases.get(clean_base, clean_base))

    @staticmethod
    def _parse_values(
        lines: list[str], curve_count: int, warnings: list[str]
    ) -> list[float]:
        values: list[float] = []
        for token in " ".join(lines).split():
            try:
                value = float(token)
            except ValueError:
                warnings.append(f"Non-numeric token skipped: '{token}'")
                continue
            if not math.isfinite(value):
                raise ValueError("LAS data values must be finite")
            values.append(value)
        remainder = len(values) % curve_count
        if remainder:
            warnings.append(
                f"Data length ({len(values)}) not divisible by curve count ({curve_count}). Truncating {remainder} trailing values."
            )
            values = values[:-remainder]
        return values

    @staticmethod
    def _parse_header_line(line: str) -> HeaderItem | None:
        content = line.split("#", 1)[0].strip()
        if not content or "." not in content:
            return None
        mnemonic, remainder = content.split(".", 1)
        unit_value, separator, description = remainder.partition(":")
        parts = unit_value.strip().split(None, 1)
        if not parts:
            unit, value = "", ""
        elif len(parts) == 1:
            try:
                float(parts[0])
                unit, value = "", parts[0]
            except ValueError:
                unit, value = parts[0], ""
        else:
            unit, value = parts[0], parts[1].strip()
        return HeaderItem(
            mnemonic=mnemonic.strip().upper(),
            unit=unit.upper(),
            value=value,
            description=description.strip() if separator else "",
        )

    @staticmethod
    def _well_number(
        well_info: dict[str, dict[str, Any] | Any], key: str, default: float
    ) -> float:
        item = well_info.get(key)
        if not isinstance(item, dict):
            return default
        try:
            return float(item.get("value", default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _well_text(
        well_info: dict[str, dict[str, Any] | Any], keys: tuple[str, ...]
    ) -> str:
        for key in keys:
            item = well_info.get(key)
            if isinstance(item, dict) and item.get("value"):
                return str(item["value"])
        return ""


class ParsedLasWriter:
    """Persist parsed LAS output as formatted JSON."""

    def __init__(self, output_path: Path, payload: dict[str, Any]) -> None:
        self._output_path = output_path
        self._payload = payload

    def write(self) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path.write_text(
            json.dumps(self._payload, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Parse one confined LAS file from an already-parsed request object."""
    try:
        if not isinstance(request, dict):
            raise ValueError("input must be a JSON object")
        workspace_dir = request.get("workspace_dir")
        las_path_value = request.get("las_path")
        if not isinstance(workspace_dir, str) or not workspace_dir:
            raise ValueError("workspace_dir is required")
        if not isinstance(las_path_value, str) or not las_path_value:
            raise ValueError("las_path is required")
        las_path = WorkspacePathResolver(
            workspace_dir, las_path_value, "las_path"
        ).resolve()
        if not las_path.is_file():
            raise ValueError(f"LAS file not found: {las_path_value}")
        aliases = AliasTableBuilder(request.get("aliases")).build()
        parsed = LasParser(
            las_path.read_text(encoding="utf-8", errors="replace"), aliases
        ).parse()
        data_root = str(request.get("data_root", DEFAULT_DATA_ROOT))
        output_root = WorkspacePathResolver(
            workspace_dir, data_root, "data_root"
        ).resolve()
        well_id = str(
            request.get("well_id")
            or parsed.well_info.get("_well_name")
            or las_path.stem
        )
        if not WELL_ID_PATTERN.fullmatch(well_id):
            raise ValueError("well_id must match ^[A-Za-z0-9._-]+$")
        available = list(parsed.data_arrays)
        present = [name for name in REQUIRED_CURVES if name in available]
        missing = [name for name in REQUIRED_CURVES if name not in available]
        warnings = list(parsed.warnings)
        if missing:
            warnings.append(f"Missing required curves: {missing}")
        if "NPHI" not in available:
            warnings.append("NPHI not found; neutron-density crossover unavailable")
        depth = parsed.data_arrays.get(
            "DEPTH", next(iter(parsed.data_arrays.values()), [])
        )
        finite_depth = [value for value in depth if value is not None]
        output_path = output_root / f"{well_id}_parsed.json"
        payload = {
            "status": "success",
            "well_id": well_id,
            "source_path": str(las_path),
            "version": parsed.version,
            "wrap": parsed.wrap,
            "well_info": parsed.well_info,
            "curves": [
                {
                    "mnemonic": curve.mnemonic,
                    "unit": curve.unit,
                    "description": curve.description,
                    "standard_name": curve.standard_name,
                }
                for curve in parsed.curves
            ],
            "alias_mapping": {
                curve.mnemonic: curve.standard_name for curve in parsed.curves
            },
            "sample_count": len(depth),
            "depth_range": {
                "minimum": min(finite_depth) if finite_depth else None,
                "maximum": max(finite_depth) if finite_depth else None,
                "unit": parsed.curves[0].unit if parsed.curves else "",
            },
            "required_curves": {
                "valid": not missing,
                "present": present,
                "missing": missing,
                "available": available,
            },
            "warnings": warnings,
            "data_arrays": parsed.data_arrays,
            "output_path": str(output_path),
        }
        ParsedLasWriter(output_path, payload).write()
        return payload
    except (ValueError, OSError, json.JSONDecodeError) as error:
        return {"status": "error", "error": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a confined LAS 2.0 file.")
    parser.add_argument("--input", required=True, help="JSON request object")
    args = parser.parse_args()
    try:
        request = json.loads(args.input)
    except json.JSONDecodeError as error:
        logger.info(json.dumps({"status": "error", "error": str(error)}))
        return 2
    result = run(request)
    logger.info(json.dumps(result, separators=(",", ":")))
    return 0 if result.get("status") != "error" else 2


if __name__ == "__main__":
    sys.exit(main())
