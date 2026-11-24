"""
description: Builds a small, valid results dict for the report unit tests with no files.
last_updated: 2026-11-24
"""

from __future__ import annotations

from recon_models import (
    LineResult,
    Linkage,
    Nature,
    ProofCheck,
    ReconResult,
    Totals,
    Window,
)


def line(key: str, plan: float, actual: float, **overrides: object) -> LineResult:
    """One planned cost line with year-to-date plan and actual."""
    department, account = key.split(" | ")
    values: dict[str, object] = {
        "key": key,
        "keys": {"department": department, "account": account},
        "nature": Nature.COST,
        "in_plan": True,
        "plan_ytd": plan,
        "actual_ytd": actual,
        "var_ytd": actual - plan,
        "var_pct_ytd": (actual - plan) / plan if plan else None,
        "plan_cur": plan / 9,
        "actual_cur": actual / 9,
        "var_cur": (actual - plan) / 9,
        "var_pct_cur": None,
        "plan_fy": plan * 12 / 9,
        "pending": 0.0,
        "open_commitments": 0.0,
        "committed": actual,
        "available": plan * 12 / 9 - actual,
    }
    values.update(overrides)
    return LineResult(**values)


def result(lines: list[LineResult], **overrides: object) -> dict:
    """A results dict shaped like results.json, totalled from the lines."""
    plan_ytd = sum(item.plan_ytd for item in lines)
    actual_ytd = sum(item.actual_ytd for item in lines)
    totals = Totals(
        plan_ytd=plan_ytd,
        actual_ytd=actual_ytd,
        var_ytd=actual_ytd - plan_ytd,
        var_pct_ytd=(actual_ytd - plan_ytd) / plan_ytd if plan_ytd else None,
        plan_cur=sum(item.plan_cur for item in lines),
        actual_cur=sum(item.actual_cur for item in lines),
        var_cur=sum(item.var_cur for item in lines),
        plan_fy=sum(item.plan_fy for item in lines),
        pending=0.0,
        open_commitments=0.0,
        committed=actual_ytd,
        available=sum(item.available for item in lines),
        unplanned_ytd=sum(item.actual_ytd for item in lines if not item.in_plan),
        open_period_actuals=0.0,
        materiality_ytd=1000.0,
        materiality_cur=500.0,
    )
    periods = [f"2026-{m:02d}" for m in range(1, 13)]
    values: dict[str, object] = {
        "engine_version": "test",
        "name": "Test reconciliation",
        "reporting_currency": "USD",
        "currency_symbol": "$",
        "sign_convention": "Variance is actual minus plan.",
        "grain": ["department", "account"],
        "window": Window(
            horizon_start="2026-01",
            horizon_end="2026-12",
            last_closed="2026-09",
            ytd_periods=periods[:9],
            horizon_periods=periods,
            elapsed_share=0.75,
            as_of_date="2026-10-14",
        ),
        "totals": totals,
        "linkage": Linkage(
            method="none", confidence="n/a", matched_share=None, note="No POs."
        ),
        "lines": lines,
        "monthly": [],
        "flags": [],
        "commitments": [],
        "invoices": [],
        "unplanned": [],
        "headcount": [],
        "headcount_flags": [],
        "tie_out": [],
        "proof": [
            ProofCheck(
                name="GL actuals are each counted once",
                left=actual_ytd,
                right=actual_ytd,
                difference=0.0,
                passed=True,
                explanation="test",
            )
        ],
        "findings": [],
        "fx_used": [],
        "spec": {"rules": {}, "assumptions": []},
    }
    values.update(overrides)
    return ReconResult(**values).model_dump(mode="json")
