"""
description: Pure outlier screens for run_reconciliation.py: line, document and headcount flags with reasons written from the numbers.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math
from datetime import date, datetime

import numpy as np
from recon_models import (
    CommitmentRow,
    FlagItem,
    HeadcountRow,
    InvoiceRow,
    LineResult,
    Nature,
    Rules,
    Tier,
)
from recon_parsing import (
    clip_text,
    modified_z,
    money,
    pct_text,
    safe_pct,
    shift_period,
)


class OutlierScreen:
    """Flags lines and documents that need inspection, with a reason written from the numbers."""

    def __init__(
        self, rules: Rules, symbol: str, m_ytd: float, m_cur: float, last_closed: str
    ) -> None:
        self.rules = rules
        self.symbol = symbol
        self.m_ytd = m_ytd
        self.m_cur = m_cur
        self.last_closed = last_closed

    def screen(
        self,
        lines: list[LineResult],
        history: dict[str, dict[str, float]],
        plan_hist: dict[str, dict[str, float]],
        commitments: list[CommitmentRow],
        invoices: list[InvoiceRow],
        as_of: date,
    ) -> list[FlagItem]:
        flags: list[FlagItem] = []
        scaled_ytd = np.array(
            [
                self._scaled(x.var_ytd, x.plan_ytd, x.actual_ytd)
                for x in lines
                if x.in_plan
            ]
        )
        scaled_cur = np.array(
            [
                self._scaled(x.var_cur, x.plan_cur, x.actual_cur)
                for x in lines
                if x.in_plan
            ]
        )
        for line in lines:
            flags.extend(
                self._line_flags(
                    line,
                    scaled_ytd,
                    scaled_cur,
                    history.get(line.key, {}),
                    plan_hist.get(line.key, {}),
                )
            )
        flags.extend(self._document_flags(commitments, invoices, as_of))
        flags.sort(key=lambda f: (0 if f.tier == Tier.INSPECT else 1, -f.priority))
        for i, f in enumerate(flags, start=1):
            f.id = f"F{i:02d}"
        return flags

    def _scaled(self, var: float, plan: float, actual: float) -> float:
        return var / math.sqrt(abs(plan) + abs(actual) + 1.0)

    def _line_flags(
        self,
        line: LineResult,
        scaled_ytd: np.ndarray,
        scaled_cur: np.ndarray,
        hist: dict[str, float],
        plan_hist: dict[str, float],
    ) -> list[FlagItem]:
        out: list[FlagItem] = []
        s = self.symbol
        word = "over" if line.var_ytd > 0 else "under"
        if not line.in_plan:
            if abs(line.actual_ytd) >= self.m_cur:
                tier = (
                    Tier.INSPECT
                    if abs(line.actual_ytd) >= self.m_ytd * 0.5
                    else Tier.WATCH
                )
                out.append(
                    self._flag(
                        line,
                        tier,
                        "unplanned",
                        "ytd",
                        line.actual_ytd,
                        ["unplanned"],
                        f"{money(s, line.actual_ytd)} posted year to date with no plan at this grain. Check the coding, or whether a plan line is missing.",
                        line.plan_ytd,
                        line.actual_ytd,
                        line.var_ytd,
                        None,
                    )
                )
            return out
        # Year to date
        tests: list[str] = []
        if abs(line.var_ytd) >= self.m_ytd:
            tests.append("material")
        pct = line.var_pct_ytd
        if pct is not None and abs(pct) >= self.rules.variance_pct:
            tests.append("relative")
        z = (
            modified_z(
                scaled_ytd, self._scaled(line.var_ytd, line.plan_ytd, line.actual_ytd)
            )
            if scaled_ytd.size >= 5
            else None
        )
        if z is not None and abs(z) >= self.rules.z_threshold:
            tests.append("cross_section")
        if "material" in tests and len(tests) > 1:
            sentence = f"{money(s, abs(line.var_ytd))} {word} plan year to date ({pct_text(pct)}) against {money(s, line.plan_ytd)} planned."
            if "cross_section" in tests:
                sentence += f" Unusual against the other lines (robust z-score {z:+.1f}; beyond 3.5 is unusual)."
            out.append(
                self._flag(
                    line,
                    Tier.INSPECT,
                    "overspend" if line.var_ytd > 0 else "underspend",
                    "ytd",
                    line.var_ytd,
                    tests,
                    sentence,
                    line.plan_ytd,
                    line.actual_ytd,
                    line.var_ytd,
                    pct,
                )
            )
        elif (
            tests == ["material"]
            and pct is not None
            and abs(pct) >= self.rules.variance_pct / 2
        ) or (
            "material" not in tests
            and "cross_section" in tests
            and abs(line.var_ytd) >= self.m_ytd * 0.5
        ):
            out.append(
                self._flag(
                    line,
                    Tier.WATCH,
                    "overspend" if line.var_ytd > 0 else "underspend",
                    "ytd",
                    line.var_ytd,
                    tests,
                    f"{money(s, abs(line.var_ytd))} {word} plan year to date ({pct_text(pct)}).",
                    line.plan_ytd,
                    line.actual_ytd,
                    line.var_ytd,
                    pct,
                )
            )
        # Current period
        cur_tests: list[str] = []
        if abs(line.var_cur) >= self.m_cur:
            cur_tests.append("material")
        cpct = line.var_pct_cur
        if cpct is not None and abs(cpct) >= self.rules.variance_pct:
            cur_tests.append("relative")
        prior = [hist[p] for p in sorted(hist) if p < self.last_closed]
        hz = None
        if len(prior) >= self.rules.min_history:
            hz = modified_z(np.array(prior[-12:]), line.actual_cur)
            plan_prior = [
                plan_hist[p] for p in sorted(plan_hist) if p < self.last_closed
            ][-12:]
            pz = (
                modified_z(np.array(plan_prior), line.plan_cur)
                if len(plan_prior) >= self.rules.min_history
                else None
            )
            planned_jump = (
                pz is not None
                and abs(pz) >= self.rules.z_threshold
                and (pz > 0) == (hz is not None and hz > 0)
            )
            if (
                hz is not None
                and abs(hz) >= self.rules.z_threshold
                and not planned_jump
            ):
                cur_tests.append("history_spike")
        timing = self._timing(line, hist, plan_hist)
        if "material" in cur_tests and len(cur_tests) > 1:
            cword = "over" if line.var_cur > 0 else "under"
            sentence = f"{self._month(self.last_closed)}: {money(s, abs(line.var_cur))} {cword} plan ({pct_text(cpct)})."
            if "history_spike" in cur_tests:
                sentence += f" Far outside this line's own last {min(len(prior), 12)} months (robust z-score {hz:+.1f}; beyond 3.5 is unusual)."
            tier = Tier.INSPECT
            kind = (
                "spike"
                if "history_spike" in cur_tests
                else ("overspend" if line.var_cur > 0 else "underspend")
            )
            if timing:
                cur_tests.append("timing")
                tier = Tier.WATCH
                kind = "timing"
                sentence += f" Likely timing: it reverses {money(s, abs(timing))} {'under' if timing < 0 else 'over'} plan in the prior {self.rules.timing_window} months, so year to date is close to plan."
            out.append(
                self._flag(
                    line,
                    tier,
                    kind,
                    "current",
                    line.var_cur,
                    cur_tests,
                    sentence,
                    line.plan_cur,
                    line.actual_cur,
                    line.var_cur,
                    cpct,
                )
            )
        # Full year commitment
        if (
            line.nature == Nature.COST
            and line.plan_fy > 0
            and line.available < 0
            and abs(line.available) >= self.m_ytd * 0.5
        ):
            tier = Tier.INSPECT if abs(line.available) >= self.m_ytd else Tier.WATCH
            out.append(
                self._flag(
                    line,
                    tier,
                    "committed_beyond_budget",
                    "full_year",
                    line.available,
                    ["committed"],
                    f"Actuals, pending invoices and open POs total {money(s, line.committed)} against a {money(s, line.plan_fy)} full-year budget: {money(s, -line.available)} already committed beyond budget.",
                    line.plan_fy,
                    line.committed,
                    -line.available,
                    safe_pct(-line.available, line.plan_fy),
                )
            )
        if (
            line.nature == Nature.COST
            and line.actual_ytd < 0
            and abs(line.actual_ytd) >= self.m_ytd * 0.5
        ):
            out.append(
                self._flag(
                    line,
                    Tier.WATCH,
                    "credit_balance",
                    "ytd",
                    line.actual_ytd,
                    ["sign"],
                    f"Cost line carries a net credit of {money(s, line.actual_ytd)} year to date. Check for a reversal, reclass or sign issue.",
                    line.plan_ytd,
                    line.actual_ytd,
                    line.var_ytd,
                    None,
                )
            )
        return out

    def _timing(
        self, line: LineResult, hist: dict[str, float], plan_hist: dict[str, float]
    ) -> float:
        prior_periods = [
            shift_period(self.last_closed, -k)
            for k in range(1, self.rules.timing_window + 1)
        ]
        prior_var = sum(hist.get(p, 0.0) - plan_hist.get(p, 0.0) for p in prior_periods)
        if line.var_cur == 0 or prior_var == 0 or (prior_var > 0) == (line.var_cur > 0):
            return 0.0
        if abs(line.var_cur + prior_var) <= self.rules.timing_offset_share * abs(
            line.var_cur
        ):
            return prior_var
        return 0.0

    def _document_flags(
        self, commitments: list[CommitmentRow], invoices: list[InvoiceRow], as_of: date
    ) -> list[FlagItem]:
        s = self.symbol
        out: list[FlagItem] = []
        by_po: dict[str, list[CommitmentRow]] = {}
        for c in commitments:
            by_po.setdefault(c.po_number, []).append(c)
        for po, rows in by_po.items():
            overrun = sum(r.overrun for r in rows)
            ordered = sum(r.ordered for r in rows)
            open_amt = sum(r.open_amount for r in rows)
            first = rows[0]
            if overrun > max(0.01 * ordered, 1.0):
                tier = Tier.INSPECT if overrun >= self.m_cur else Tier.WATCH
                out.append(
                    self._doc(
                        first,
                        tier,
                        "po_overrun",
                        overrun,
                        ["document"],
                        f"PO {clip_text(po)} ({clip_text(first.vendor) or 'vendor not given'}): posted and pending invoices exceed the {money(s, ordered)} ordered by {money(s, overrun)}.",
                        po,
                    )
                )
            need_by = first.need_by
            if open_amt > 0 and need_by:
                age = (as_of - date(int(need_by[:4]), int(need_by[5:7]), 1)).days
                if age > self.rules.stale_commitment_days:
                    tier = Tier.INSPECT if open_amt >= self.m_cur else Tier.WATCH
                    out.append(
                        self._doc(
                            first,
                            tier,
                            "stale_commitment",
                            open_amt,
                            ["document"],
                            f"PO {clip_text(po)} still holds {money(s, open_amt)} open, {age} days past its need-by month {need_by}. Close it to release budget, or confirm the spend is still coming.",
                            po,
                        )
                    )
        for inv in invoices:
            if (
                inv.posted is False
                and inv.days_unposted is not None
                and inv.days_unposted > self.rules.unposted_invoice_days
            ):
                tier = Tier.INSPECT if abs(inv.amount) >= self.m_cur else Tier.WATCH
                out.append(
                    FlagItem(
                        id="",
                        tier=tier,
                        kind="aged_unposted_invoice",
                        view="document",
                        key=inv.key,
                        keys={},
                        amount=inv.amount,
                        tests=["document"],
                        reason=f"Invoice {clip_text(inv.invoice_number)} ({clip_text(inv.vendor) or 'vendor not given'}) for {money(s, inv.amount)} has waited {inv.days_unposted} days without reaching the GL. It is counted as pending, not as actuals.",
                        priority=abs(inv.amount) / max(self.m_cur, 1.0),
                        reference=inv.invoice_number,
                    )
                )
        out.extend(self._duplicates(invoices))
        return out

    def _duplicates(self, invoices: list[InvoiceRow]) -> list[FlagItem]:
        s = self.symbol
        out: list[FlagItem] = []
        seen_numbers: dict[str, InvoiceRow] = {}
        for inv in invoices:
            if inv.invoice_number and inv.invoice_number in seen_numbers:
                out.append(
                    FlagItem(
                        id="",
                        tier=Tier.INSPECT,
                        kind="duplicate_invoice",
                        view="document",
                        key=inv.key,
                        keys={},
                        amount=inv.amount,
                        tests=["document"],
                        reason=f"Invoice number {clip_text(inv.invoice_number)} appears twice ({money(s, inv.amount)}). Confirm it was not paid or posted twice.",
                        priority=abs(inv.amount) / max(self.m_cur, 1.0) + 1,
                        reference=inv.invoice_number,
                    )
                )
            seen_numbers.setdefault(inv.invoice_number, inv)
        dated = sorted(
            [i for i in invoices if i.invoice_date and i.vendor],
            key=lambda i: (i.vendor, round(i.amount, 2), i.invoice_date),
        )
        for a, b in zip(dated, dated[1:], strict=False):
            if (
                a.vendor == b.vendor
                and round(a.amount, 2) == round(b.amount, 2)
                and a.invoice_number != b.invoice_number
                and abs(a.amount) > 0
            ):
                gap = abs(
                    (
                        date.fromisoformat(b.invoice_date)
                        - date.fromisoformat(a.invoice_date)
                    ).days
                )
                if gap <= self.rules.duplicate_window_days:
                    out.append(
                        FlagItem(
                            id="",
                            tier=Tier.INSPECT,
                            kind="possible_duplicate_invoice",
                            view="document",
                            key=b.key,
                            keys={},
                            amount=b.amount,
                            tests=["document"],
                            reason=f"Invoices {clip_text(a.invoice_number)} and {clip_text(b.invoice_number)} from {clip_text(b.vendor)} are both {money(s, b.amount)}, {gap} days apart. Possible duplicate billing.",
                            priority=abs(b.amount) / max(self.m_cur, 1.0) + 1,
                            reference=f"{a.invoice_number}, {b.invoice_number}",
                        )
                    )
        return out

    def _flag(
        self,
        line: LineResult,
        tier: Tier,
        kind: str,
        view: str,
        amount: float,
        tests: list[str],
        reason: str,
        plan: float | None,
        actual: float | None,
        var: float | None,
        pct: float | None,
    ) -> FlagItem:
        floor = self.m_cur if view == "current" else self.m_ytd
        weight = 1.0 + 0.5 * (len(tests) - 1)
        return FlagItem(
            id="",
            tier=tier,
            kind=kind,
            view=view,
            key=line.key,
            keys=line.keys,
            amount=amount,
            plan=plan,
            actual=actual,
            variance=var,
            variance_pct=pct,
            tests=tests,
            reason=reason,
            priority=abs(amount) / max(floor, 1.0) * weight,
        )

    def _doc(
        self,
        row: CommitmentRow,
        tier: Tier,
        kind: str,
        amount: float,
        tests: list[str],
        reason: str,
        ref: str,
    ) -> FlagItem:
        return FlagItem(
            id="",
            tier=tier,
            kind=kind,
            view="document",
            key=row.key,
            keys=row.keys,
            amount=amount,
            tests=tests,
            reason=reason,
            priority=abs(amount) / max(self.m_cur, 1.0),
            reference=ref,
        )

    def _month(self, period: str) -> str:
        return datetime(int(period[:4]), int(period[5:]), 1).strftime("%b %Y")


class HeadcountScreen:
    """Compares planned and actual heads at the last closed period. Heads are a stock: never summed across months."""

    def __init__(self, rules: Rules, last_closed: str) -> None:
        self.rules = rules
        self.last_closed = last_closed

    def screen(self, rows: list[HeadcountRow]) -> list[FlagItem]:
        current = [r for r in rows if r.period == self.last_closed]
        total_plan = sum(r.plan for r in current)
        floor = (
            self.rules.headcount_floor
            if self.rules.headcount_floor is not None
            else max(1.0, round(0.01 * total_plan))
        )
        out: list[FlagItem] = []
        for r in current:
            var = r.actual - r.plan
            pct = safe_pct(var, r.plan)
            if abs(var) >= floor and (
                pct is None or abs(pct) >= self.rules.headcount_pct
            ):
                word = "above" if var > 0 else "below"
                reason = f"{r.actual:,.0f} heads against {r.plan:,.0f} planned at {self.last_closed}: {abs(var):,.0f} {word} plan ({pct_text(pct)})."
                tests = ["material", "relative"]
                if r.open_reqs and var < 0 and r.actual + r.open_reqs > r.plan:
                    reason += f" Filling all {r.open_reqs:,.0f} open requisitions would land {r.actual + r.open_reqs - r.plan:,.0f} above plan."
                    tests.append("committed")
                out.append(
                    FlagItem(
                        id="",
                        tier=Tier.INSPECT,
                        kind="headcount_variance",
                        view="current",
                        key=r.key,
                        keys=r.keys,
                        amount=var,
                        plan=r.plan,
                        actual=r.actual,
                        variance=var,
                        variance_pct=pct,
                        tests=tests,
                        reason=reason,
                        priority=abs(var) / floor,
                    )
                )
            elif r.open_reqs and r.actual + r.open_reqs - r.plan >= floor:
                out.append(
                    FlagItem(
                        id="",
                        tier=Tier.WATCH,
                        kind="headcount_committed",
                        view="current",
                        key=r.key,
                        keys=r.keys,
                        amount=r.actual + r.open_reqs - r.plan,
                        plan=r.plan,
                        actual=r.actual,
                        tests=["committed"],
                        priority=1.0,
                        reason=f"{r.actual:,.0f} heads plus {r.open_reqs:,.0f} open requisitions would exceed the {r.plan:,.0f} plan by {r.actual + r.open_reqs - r.plan:,.0f}.",
                    )
                )
        out.sort(key=lambda f: -f.priority)
        for i, f in enumerate(out, start=1):
            f.id = f"H{i:02d}"
        return out
