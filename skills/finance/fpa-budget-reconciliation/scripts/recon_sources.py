"""
description: I/O for run_reconciliation.py: reads each CSV or Excel source and the spec JSON, and normalizes a source's filters, column map, layout, numbers and periods.
last_updated: 2026-11-24
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from recon_models import (
    FilterAction,
    Finding,
    Layout,
    ReconSpec,
    SourceSpec,
    SpecError,
)
from recon_parsing import (
    PeriodParser,
    file_data,
    normal_text,
    to_number,
)


class TableReader:
    """Reads one CSV or Excel sheet with a header row into a DataFrame of strings and numbers."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def read(self, spec: SourceSpec) -> pd.DataFrame:
        path = Path(spec.path)
        path = path if path.is_absolute() else self.base_dir / path
        if not path.exists():
            raise SpecError(f"File not found: {path}")
        skip = max(spec.header_row - 1, 0)
        suffix = path.suffix.lower()
        if suffix in {".csv", ".txt"}:
            return pd.read_csv(
                path, skiprows=skip, dtype=object, encoding_errors="replace"
            )
        if suffix in {".xlsx", ".xlsm"}:
            sheet = spec.sheet if spec.sheet else 0
            return pd.read_excel(
                path, sheet_name=sheet, skiprows=skip, dtype=object, engine="openpyxl"
            )
        raise SpecError(
            f"Unsupported file type {suffix} for {path.name}; save it as .xlsx or .csv"
        )


class SourceNormalizer:
    """Applies a SourceSpec's filters, column map, layout and sign to a raw table."""

    def __init__(
        self,
        name: str,
        spec: SourceSpec,
        periods: PeriodParser,
        findings: list[Finding],
    ) -> None:
        self.name = name
        self.spec = spec
        self.periods = periods
        self.findings = findings

    def normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        raw = raw.dropna(how="all")
        raw.columns = [normal_text(c) for c in raw.columns]
        loaded = len(raw)
        for flt in self.spec.filters:
            if flt.column not in raw.columns:
                raise SpecError(
                    f"{self.name}: filter column not in file; {file_data(flt.column)}"
                )
            wanted = {v.strip().lower() for v in flt.values}
            hit = raw[flt.column].map(
                lambda x, wanted=wanted: normal_text(x).lower() in wanted
            )
            raw = raw[hit] if flt.action == FilterAction.INCLUDE else raw[~hit]
        missing = [src for src in self.spec.columns.values() if src not in raw.columns]
        if missing:
            raise SpecError(
                f"{self.name}: columns not found {file_data(missing)}; "
                f"available {file_data(list(raw.columns)[:40])}"
            )
        if self.spec.layout == Layout.WIDE:
            raw = self._melt(raw)
        out = pd.DataFrame(
            {canon: raw[src].values for canon, src in self.spec.columns.items()}
        )
        if self.spec.layout == Layout.WIDE:
            out["period"] = raw["__period"].values
            out["amount"] = raw["__amount"].values
        debit_credit = "debit" in out.columns or "credit" in out.columns
        bad_rows = pd.Series(False, index=out.index)
        bad_columns = []
        for col in (
            "debit",
            "credit",
            "amount",
            "ordered",
            "received",
            "invoiced",
            "open_amount",
            "rate",
            "plan_heads",
            "actual_heads",
            "open_reqs",
        ):
            if col not in out.columns or (col == "amount" and debit_credit):
                continue
            numbers = []
            for index, value in out[col].items():
                # A blank debit or credit denotes the unused side of an entry.
                if col in {"debit", "credit"} and (
                    pd.isna(value) or not normal_text(value)
                ):
                    numbers.append(0.0)
                    continue
                try:
                    numbers.append(to_number(value))
                except ValueError:
                    bad_rows.loc[index] = True
                    if col not in bad_columns:
                        bad_columns.append(col)
                    numbers.append(float("nan"))
            out[col] = pd.Series(numbers, index=out.index, dtype=float)
        bad = int(bad_rows.sum())
        if bad:
            self.findings.append(
                Finding(
                    code=f"{self.name}_number_unreadable",
                    severity="error",
                    count=bad,
                    message=(
                        f"{bad} {self.name} rows have unreadable or non-finite "
                        f"numbers in {', '.join(bad_columns)}; they are excluded "
                        "and counted in the tie-out. Totals are incomplete."
                    ),
                )
            )
            out = out.loc[~bad_rows].copy()
        if debit_credit:
            out["amount"] = out.get("debit", 0.0) - out.get("credit", 0.0)
        if "amount" in out.columns:
            out["amount"] = out["amount"] * self.spec.sign
        for col in ("ordered", "open_amount", "received", "invoiced"):
            if col in out.columns:
                out[col] = out[col] * self.spec.sign
        if "period" in out.columns:
            parsed = out["period"].map(self.periods.parse)
            bad = int(parsed.isna().sum())
            if bad:
                self.findings.append(
                    Finding(
                        code=f"{self.name}_period_unreadable",
                        severity="warning",
                        count=bad,
                        message=f"{bad} {self.name} rows have a period the skill could not read; they are left out and listed in the tie-out.",
                    )
                )
            out["period"] = parsed
        if "currency" not in out.columns:
            out["currency"] = self.spec.default_currency or ""
        out["currency"] = out["currency"].map(lambda x: normal_text(x).upper())
        out.attrs["loaded_rows"] = loaded
        return out

    def _melt(self, raw: pd.DataFrame) -> pd.DataFrame:
        if not self.spec.period_columns:
            raise SpecError(f"{self.name}: wide layout needs period_columns")
        absent = [c for c in self.spec.period_columns if c not in raw.columns]
        if absent:
            raise SpecError(
                f"{self.name}: period columns not found {file_data(absent)}"
            )
        id_cols = list(dict.fromkeys(self.spec.columns.values()))
        long = raw.melt(
            id_vars=id_cols,
            value_vars=self.spec.period_columns,
            var_name="__period",
            value_name="__amount",
        )
        return long


class SpecReader:
    """Reads and validates the spec JSON."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> ReconSpec:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return ReconSpec.model_validate(data)
