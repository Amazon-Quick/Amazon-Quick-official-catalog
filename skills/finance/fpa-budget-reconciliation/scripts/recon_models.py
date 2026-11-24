"""
description: Spec and result data models for run_reconciliation.py: enums, the reconciliation spec schema, every result row type and SpecError.
last_updated: 2026-11-24
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DEFAULT_CLOSED = [
    "closed",
    "cancelled",
    "canceled",
    "complete",
    "completed",
    "finally closed",
]
DEFAULT_POSTED = ["posted", "paid", "accounted", "recorded"]


class Layout(StrEnum):
    LONG = "long"
    WIDE = "wide"


class FilterAction(StrEnum):
    INCLUDE = "include"
    EXCLUDE = "exclude"


class CommitmentLink(StrEnum):
    AUTO = "auto"
    BY_REFERENCE = "by_reference"
    OPEN_COLUMN = "open_column"
    ORDERED_LESS_INVOICED = "ordered_less_invoiced"


class OpenBasis(StrEnum):
    NET_OF_INVOICED = "net_of_invoiced"
    NET_OF_POSTED = "net_of_posted"


class RateDirection(StrEnum):
    TO_REPORTING = "to_reporting"
    FROM_REPORTING = "from_reporting"


class Nature(StrEnum):
    COST = "cost"
    REVENUE = "revenue"


class Tier(StrEnum):
    INSPECT = "inspect"
    WATCH = "watch"


class FilterSpec(BaseModel):
    column: str
    values: list[str]
    action: FilterAction = FilterAction.EXCLUDE


class SourceSpec(BaseModel):
    path: str
    sheet: str | None = None
    header_row: int = 1
    columns: dict[str, str] = Field(default_factory=dict)
    layout: Layout = Layout.LONG
    period_columns: list[str] = Field(default_factory=list)
    sign: int = 1
    filters: list[FilterSpec] = Field(default_factory=list)
    default_currency: str | None = None


class FxSpec(SourceSpec):
    rate_direction: RateDirection = RateDirection.TO_REPORTING


class HierarchySpec(BaseModel):
    dimension: str
    path: str | None = None
    sheet: str | None = None
    child_column: str = "child"
    parent_column: str = "parent"
    mapping: dict[str, str] = Field(default_factory=dict)


class Sources(BaseModel):
    plan: SourceSpec
    actuals: SourceSpec
    commitments: SourceSpec | None = None
    invoices: SourceSpec | None = None
    fx: FxSpec | None = None
    headcount: SourceSpec | None = None


class Rules(BaseModel):
    materiality_amount: float | None = None
    materiality_share: float = 0.005
    variance_pct: float = 0.10
    z_threshold: float = 3.5
    min_history: int = 6
    timing_window: int = 2
    timing_offset_share: float = 0.25
    stale_commitment_days: int = 90
    unposted_invoice_days: int = 30
    duplicate_window_days: int = 7
    commitment_link: CommitmentLink = CommitmentLink.AUTO
    open_basis: OpenBasis = OpenBasis.NET_OF_INVOICED
    accruals_in_gl: bool | None = None
    closed_statuses: list[str] = Field(default_factory=lambda: list(DEFAULT_CLOSED))
    posted_invoice_statuses: list[str] = Field(
        default_factory=lambda: list(DEFAULT_POSTED)
    )
    revenue: FilterSpec | None = None
    headcount_floor: float | None = None
    headcount_pct: float = 0.05


class ReconSpec(BaseModel):
    name: str = "Budget reconciliation"
    reporting_currency: str = "USD"
    last_closed_period: str
    fiscal_year_start_month: int = 1
    fiscal_year_label: str = "end"
    date_order: Literal["day_first", "month_first"] | None = None
    horizon_start: str | None = None
    horizon_end: str | None = None
    as_of_date: str | None = None
    grain: list[str]
    assumptions: list[str] = Field(default_factory=list)
    data_notice: str | None = None
    sign_convention: str = "Variance is actual minus plan. For cost lines a positive variance is over budget (unfavorable); for revenue lines a positive variance is favorable."
    sources: Sources
    hierarchies: list[HierarchySpec] = Field(default_factory=list)
    rules: Rules = Field(default_factory=Rules)

    @field_validator("reporting_currency")
    @classmethod
    def valid_reporting_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("reporting_currency must be a three-letter currency code")
        return value


class Finding(BaseModel):
    code: str
    severity: str
    message: str
    amount: float = 0.0
    count: int = 0


class LineResult(BaseModel):
    key: str
    keys: dict[str, str]
    nature: Nature
    in_plan: bool
    plan_ytd: float
    actual_ytd: float
    var_ytd: float
    var_pct_ytd: float | None
    plan_cur: float
    actual_cur: float
    var_cur: float
    var_pct_cur: float | None
    plan_fy: float
    pending: float
    open_commitments: float
    committed: float
    available: float
    tier: Tier | None = None
    flags: list[str] = Field(default_factory=list)


class MonthlyRow(BaseModel):
    key: str
    period: str
    plan: float
    actual: float


class FlagItem(BaseModel):
    id: str
    tier: Tier
    kind: str
    view: str
    key: str
    keys: dict[str, str]
    amount: float
    plan: float | None = None
    actual: float | None = None
    variance: float | None = None
    variance_pct: float | None = None
    tests: list[str]
    reason: str
    priority: float
    reference: str | None = None


class CommitmentRow(BaseModel):
    po_number: str
    po_line: str
    key: str
    keys: dict[str, str]
    vendor: str
    status: str
    need_by: str | None
    ordered: float
    posted: float
    pending: float
    open_amount: float
    released: float
    overrun: float
    link: str


class InvoiceRow(BaseModel):
    invoice_number: str
    po_number: str
    key: str
    vendor: str
    invoice_date: str | None
    amount: float
    status: str
    posted: bool | None
    days_unposted: int | None


class UnplannedRow(BaseModel):
    key: str
    keys: dict[str, str]
    source_value: str
    actual_ytd: float


class HeadcountRow(BaseModel):
    key: str
    keys: dict[str, str]
    period: str
    plan: float
    actual: float
    open_reqs: float | None


class DrillRow(BaseModel):
    period: str
    amount: float
    amount_source: float
    currency: str
    vendor: str
    description: str
    reference: str
    invoice_ref: str
    source_value: str


class TieOut(BaseModel):
    source: str
    label: str
    amount: float
    note: str = ""


class ProofCheck(BaseModel):
    name: str
    left: float
    right: float
    difference: float
    passed: bool
    explanation: str


class Totals(BaseModel):
    plan_ytd: float
    actual_ytd: float
    var_ytd: float
    var_pct_ytd: float | None
    plan_cur: float
    actual_cur: float
    var_cur: float
    plan_fy: float
    pending: float
    open_commitments: float
    committed: float
    available: float
    unplanned_ytd: float
    open_period_actuals: float
    materiality_ytd: float
    materiality_cur: float


class Window(BaseModel):
    horizon_start: str
    horizon_end: str
    last_closed: str
    ytd_periods: list[str]
    horizon_periods: list[str]
    elapsed_share: float
    as_of_date: str


class Linkage(BaseModel):
    method: str
    confidence: str
    matched_share: float | None
    note: str


class ReconResult(BaseModel):
    engine_version: str
    name: str
    reporting_currency: str
    currency_symbol: str
    sign_convention: str
    grain: list[str]
    window: Window
    totals: Totals
    linkage: Linkage
    lines: list[LineResult]
    monthly: list[MonthlyRow]
    flags: list[FlagItem]
    commitments: list[CommitmentRow]
    invoices: list[InvoiceRow]
    unplanned: list[UnplannedRow]
    headcount: list[HeadcountRow]
    headcount_flags: list[FlagItem]
    tie_out: list[TieOut]
    proof: list[ProofCheck]
    findings: list[Finding]
    fx_used: list[dict[str, object]]
    spec: dict[str, object]
    source_files: list[str] = Field(default_factory=list)
    drill: list[DrillRow] = Field(default_factory=list)
    drill_key: str | None = None
    data_notice: str | None = None


class SpecError(ValueError):
    """The spec does not match the files it points at."""
