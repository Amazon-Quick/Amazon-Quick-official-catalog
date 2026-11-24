"""
description: Workbook writer for create_report.py: every sheet of the detailed workbook, with totals and variances as live formulas over the line detail.
last_updated: 2026-11-24
"""

from __future__ import annotations

from typing import BinaryIO

import xlsxwriter
from report_format import (
    KIND_LABELS,
    MUTED,
    OVER,
    UNDER,
    inspect_items,
    money,
)
from report_html import HeadlineWriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell


class WorkbookWriter:
    """Writes the detailed workbook. Totals and variances are live formulas over the detail sheets."""

    def __init__(self, result: dict, target: str | BinaryIO) -> None:
        self.r = result
        self.target = target
        self.s = result["currency_symbol"]

    def write(self) -> None:
        # Cell text from the user's files stays text: never a formula or a link.
        wb = xlsxwriter.Workbook(
            self.target,
            {"strings_to_formulas": False, "strings_to_urls": False},
        )
        self.f = self._formats(wb)
        summary = wb.add_worksheet("Summary")
        line_ref = self._lines(wb.add_worksheet("Lines"))
        self._inspect(wb.add_worksheet("Inspect"))
        self._monthly(wb.add_worksheet("Monthly"), wb.add_worksheet("Trend"))
        self._commitments(wb.add_worksheet("Commitments"))
        self._invoices(wb.add_worksheet("Invoices"))
        self._unplanned(wb.add_worksheet("Unplanned"))
        self._headcount(wb.add_worksheet("Headcount"))
        self._tieout(wb.add_worksheet("Tie-out"))
        self._fx(wb.add_worksheet("FX rates"))
        self._method(wb.add_worksheet("Method"))
        self._summary(summary, line_ref)
        wb.close()

    def _formats(self, wb: xlsxwriter.Workbook) -> dict:
        base = {"font_name": "Calibri", "font_size": 10, "valign": "top"}
        num = '#,##0;(#,##0);"-"'
        return {
            "title": wb.add_format({**base, "bold": True, "font_size": 16}),
            "sub": wb.add_format({**base, "font_color": MUTED}),
            "head": wb.add_format(
                {
                    **base,
                    "bold": True,
                    "bg_color": "#F1EFEA",
                    "bottom": 1,
                    "text_wrap": True,
                    "valign": "bottom",
                }
            ),
            "text": wb.add_format(base),
            "wrap": wb.add_format({**base, "text_wrap": True}),
            "num": wb.add_format({**base, "num_format": num}),
            "num_b": wb.add_format({**base, "num_format": num, "bold": True, "top": 1}),
            "pct": wb.add_format({**base, "num_format": "+0.0%;-0.0%;0.0%"}),
            "heads": wb.add_format({**base, "num_format": "#,##0;-#,##0;0"}),
            "rate": wb.add_format({**base, "num_format": "0.000000"}),
            "label": wb.add_format({**base, "bold": True}),
            "inspect": wb.add_format({**base, "bold": True, "font_color": OVER}),
            "watch": wb.add_format({**base, "font_color": MUTED}),
            "pass": wb.add_format({**base, "bold": True, "font_color": UNDER}),
            "fail": wb.add_format({**base, "bold": True, "font_color": OVER}),
            "over": wb.add_format({"font_color": OVER}),
            "under": wb.add_format({"font_color": UNDER}),
            "input": wb.add_format(
                {**base, "bg_color": "#FFF9E6", "border": 1, "border_color": "#E4E1DA"}
            ),
        }

    def _header(self, ws, row: int, headers: list[str], widths: list[int]) -> None:
        for c, (h, w) in enumerate(zip(headers, widths, strict=False)):
            ws.write(row, c, h, self.f["head"])
            ws.set_column(c, c, w)
        ws.freeze_panes(row + 1, 0)

    def _lines(self, ws) -> dict:
        grain = self.r["grain"]
        heads = [g.replace("_", " ").title() for g in grain] + [
            "Nature",
            "In plan",
            "Plan YTD",
            "Actual YTD",
            "Variance YTD",
            "Variance % YTD",
            "Plan month",
            "Actual month",
            "Variance month",
            "Full-year plan",
            "Pending invoices",
            "Open POs",
            "Committed",
            "Available",
            "Tier",
            "Flags",
        ]
        widths = [18] * len(grain) + [
            9,
            8,
            13,
            13,
            13,
            11,
            12,
            12,
            12,
            14,
            13,
            13,
            13,
            13,
            9,
            14,
        ]
        ws.write(0, 0, "Lines at the plan's grain", self.f["title"])
        ws.write(
            1,
            0,
            "Variance = actual - plan. Committed = actual + pending + open POs. Available = full-year plan - committed.",
            self.f["sub"],
        )
        hr = 3
        self._header(ws, hr, heads, widths)
        g = len(grain)
        col = {
            name: g + i
            for i, name in enumerate(
                [
                    "nature",
                    "in_plan",
                    "plan_ytd",
                    "actual_ytd",
                    "var_ytd",
                    "var_pct",
                    "plan_cur",
                    "actual_cur",
                    "var_cur",
                    "plan_fy",
                    "pending",
                    "open",
                    "committed",
                    "available",
                    "tier",
                    "flags",
                ]
            )
        }
        lines = []
        for src in sorted(self.r["lines"], key=lambda litem: -abs(litem["var_ytd"])):
            litem = dict(src)
            for k in (
                "plan_ytd",
                "actual_ytd",
                "plan_cur",
                "actual_cur",
                "plan_fy",
                "pending",
                "open_commitments",
            ):
                litem[k] = round(src[k], 2)
            litem["var_ytd"] = round(litem["actual_ytd"] - litem["plan_ytd"], 2)
            litem["var_cur"] = round(litem["actual_cur"] - litem["plan_cur"], 2)
            litem["committed"] = round(
                litem["actual_ytd"] + litem["pending"] + litem["open_commitments"], 2
            )
            litem["available"] = round(litem["plan_fy"] - litem["committed"], 2)
            litem["var_pct_ytd"] = (
                (litem["var_ytd"] / abs(litem["plan_ytd"]))
                if litem["plan_ytd"]
                else None
            )
            lines.append(litem)
        self.rounded_totals = {
            k: round(sum(litem[k] for litem in lines), 2)
            for k in (
                "plan_ytd",
                "actual_ytd",
                "var_ytd",
                "plan_cur",
                "actual_cur",
                "var_cur",
                "plan_fy",
                "pending",
                "open_commitments",
                "committed",
                "available",
            )
        }
        for i, litem in enumerate(lines):
            row = hr + 1 + i
            for c, d in enumerate(grain):
                ws.write(row, c, litem["keys"].get(d, ""), self.f["text"])
            ws.write(row, col["nature"], litem["nature"], self.f["text"])
            ws.write(
                row, col["in_plan"], "yes" if litem["in_plan"] else "no", self.f["text"]
            )
            for name, key in (
                ("plan_ytd", "plan_ytd"),
                ("actual_ytd", "actual_ytd"),
                ("plan_cur", "plan_cur"),
                ("actual_cur", "actual_cur"),
                ("plan_fy", "plan_fy"),
                ("pending", "pending"),
                ("open", "open_commitments"),
            ):
                ws.write_number(row, col[name], round(litem[key], 2), self.f["num"])
            c = lambda n, row=row: xl_rowcol_to_cell(row, col[n])  # noqa: E731
            ws.write_formula(
                row,
                col["var_ytd"],
                f"={c('actual_ytd')}-{c('plan_ytd')}",
                self.f["num"],
                round(litem["var_ytd"], 2),
            )
            ws.write_formula(
                row,
                col["var_pct"],
                f'=IF({c("plan_ytd")}=0,"",{c("var_ytd")}/ABS({c("plan_ytd")}))',
                self.f["pct"],
                litem["var_pct_ytd"] if litem["var_pct_ytd"] is not None else "",
            )
            ws.write_formula(
                row,
                col["var_cur"],
                f"={c('actual_cur')}-{c('plan_cur')}",
                self.f["num"],
                round(litem["var_cur"], 2),
            )
            ws.write_formula(
                row,
                col["committed"],
                f"={c('actual_ytd')}+{c('pending')}+{c('open')}",
                self.f["num"],
                round(litem["committed"], 2),
            )
            ws.write_formula(
                row,
                col["available"],
                f"={c('plan_fy')}-{c('committed')}",
                self.f["num"],
                round(litem["available"], 2),
            )
            tier = litem.get("tier") or ""
            ws.write(row, col["tier"], tier, self.f.get(tier, self.f["text"]))
            ws.write(
                row, col["flags"], ", ".join(litem.get("flags") or []), self.f["text"]
            )
        last = hr + len(lines)
        total = last + 1
        ws.write(total, 0, "Total", self.f["label"])
        sums = {}
        for name in (
            "plan_ytd",
            "actual_ytd",
            "var_ytd",
            "plan_cur",
            "actual_cur",
            "var_cur",
            "plan_fy",
            "pending",
            "open",
            "committed",
            "available",
        ):
            letter = xl_col_to_name(col[name])
            ref = f"{letter}{hr + 2}:{letter}{last + 1}"
            value = sum(
                litem[
                    {"open": "open_commitments", "var_ytd": "var_ytd"}.get(name, name)
                ]
                for litem in lines
            )
            ws.write_formula(
                total, col[name], f"=SUM({ref})", self.f["num_b"], round(value, 2)
            )
            sums[name] = f"Lines!${letter}${total + 1}"
        ws.autofilter(hr, 0, last, len(heads) - 1)
        for name in ("var_ytd", "var_cur"):
            rng = f"{xl_col_to_name(col[name])}{hr + 2}:{xl_col_to_name(col[name])}{last + 1}"
            ws.conditional_format(
                rng,
                {"type": "cell", "criteria": ">", "value": 0, "format": self.f["over"]},
            )
            ws.conditional_format(
                rng,
                {
                    "type": "cell",
                    "criteria": "<",
                    "value": 0,
                    "format": self.f["under"],
                },
            )
        avail = f"{xl_col_to_name(col['available'])}{hr + 2}:{xl_col_to_name(col['available'])}{last + 1}"
        ws.conditional_format(
            avail,
            {"type": "cell", "criteria": "<", "value": 0, "format": self.f["over"]},
        )
        return sums

    def _inspect(self, ws) -> None:
        heads = [
            "ID",
            "Tier",
            "What",
            "View",
            "Line or document",
            "Amount",
            "Plan",
            "Actual",
            "Variance",
            "Variance %",
            "Why it is flagged",
            "Tests",
            "Reference",
            "Owner",
            "Status",
            "Notes",
        ]
        widths = [6, 8, 20, 10, 28, 13, 13, 13, 13, 10, 70, 22, 16, 14, 12, 30]
        ws.write(0, 0, "Items that need inspection", self.f["title"])
        ws.write(
            1,
            0,
            "Ranked by size against the materiality floor. Owner, Status, and Notes are for your team.",
            self.f["sub"],
        )
        self._header(ws, 3, heads, widths)
        flags = self.r["flags"] + self.r["headcount_flags"]
        for i, fl in enumerate(flags):
            row = 4 + i
            label = " · ".join((fl.get("keys") or {}).values()) or fl["key"].replace(
                " | ", " · "
            )
            is_hc = fl["id"].startswith("H")
            nf = self.f["heads"] if is_hc else self.f["num"]
            vals = [
                fl["id"],
                fl["tier"],
                KIND_LABELS.get(fl["kind"], fl["kind"]),
                fl["view"],
                label,
            ]
            for c, v in enumerate(vals):
                ws.write(
                    row,
                    c,
                    v,
                    self.f.get(fl["tier"], self.f["text"])
                    if c == 1
                    else self.f["text"],
                )
            for c, key in ((5, "amount"), (6, "plan"), (7, "actual"), (8, "variance")):
                if fl.get(key) is not None:
                    ws.write_number(row, c, round(fl[key], 2), nf)
            if fl.get("variance_pct") is not None:
                ws.write_number(row, 9, fl["variance_pct"], self.f["pct"])
            ws.write(row, 10, fl["reason"], self.f["wrap"])
            ws.write(row, 11, ", ".join(fl["tests"]), self.f["text"])
            ws.write(row, 12, fl.get("reference") or "", self.f["text"])
            for c in (13, 14, 15):
                ws.write_blank(row, c, None, self.f["input"])
        if flags:
            ws.autofilter(3, 0, 3 + len(flags), len(heads) - 1)
            ws.data_validation(
                4,
                14,
                3 + len(flags),
                14,
                {
                    "validate": "list",
                    "source": ["Open", "Explained", "Fix needed", "Done"],
                },
            )

    def _monthly(self, ws, trend) -> None:
        grain = self.r["grain"]
        lookup = {litem["key"]: litem["keys"] for litem in self.r["lines"]}
        heads = [g.replace("_", " ").title() for g in grain] + [
            "Period",
            "Plan",
            "Actual",
            "Variance",
        ]
        ws.write(0, 0, "Plan and actual by line and month", self.f["title"])
        ws.write(
            1, 0, "Months after the last closed period carry plan only.", self.f["sub"]
        )
        self._header(ws, 3, heads, [18] * len(grain) + [10, 13, 13, 13])
        g = len(grain)
        rows = self.r["monthly"]
        rows = [
            {**m, "plan": round(m["plan"], 2), "actual": round(m["actual"], 2)}
            for m in rows
        ]
        for i, m in enumerate(rows):
            row = 4 + i
            keys = lookup.get(m["key"], {})
            for c, d in enumerate(grain):
                ws.write(row, c, keys.get(d, ""), self.f["text"])
            ws.write(row, g, m["period"], self.f["text"])
            ws.write_number(row, g + 1, round(m["plan"], 2), self.f["num"])
            ws.write_number(row, g + 2, round(m["actual"], 2), self.f["num"])
            ws.write_formula(
                row,
                g + 3,
                f"={xl_rowcol_to_cell(row, g + 2)}-{xl_rowcol_to_cell(row, g + 1)}",
                self.f["num"],
                round(m["actual"] - m["plan"], 2),
            )
        last = 3 + len(rows)
        if rows:
            ws.autofilter(3, 0, last, len(heads) - 1)
        trend.write(0, 0, "Totals by month", self.f["title"])
        trend.write(
            1,
            0,
            "SUMIFS over the Monthly sheet, so a filter or edit there flows through.",
            self.f["sub"],
        )
        self._header(
            trend,
            3,
            ["Period", "Plan", "Actual", "Variance", "Variance %", "Closed"],
            [10, 14, 14, 14, 11, 8],
        )
        pcol = xl_col_to_name(g)
        plan_col = xl_col_to_name(g + 1)
        act_col = xl_col_to_name(g + 2)
        last_closed = self.r["window"]["last_closed"]
        for i, p in enumerate(self.r["window"]["horizon_periods"]):
            row = 4 + i
            pv = round(sum(m["plan"] for m in rows if m["period"] == p), 2)
            av = round(sum(m["actual"] for m in rows if m["period"] == p), 2)
            trend.write(row, 0, p, self.f["text"])
            trend.write_formula(
                row,
                1,
                f"=SUMIFS(Monthly!${plan_col}$5:${plan_col}${last + 1},Monthly!${pcol}$5:${pcol}${last + 1},$A{row + 1})",
                self.f["num"],
                round(pv, 2),
            )
            trend.write_formula(
                row,
                2,
                f"=SUMIFS(Monthly!${act_col}$5:${act_col}${last + 1},Monthly!${pcol}$5:${pcol}${last + 1},$A{row + 1})",
                self.f["num"],
                round(av, 2),
            )
            trend.write_formula(
                row,
                3,
                f'=IF(F{row + 1}="yes",C{row + 1}-B{row + 1},"")',
                self.f["num"],
                round(av - pv, 2) if p <= last_closed else "",
            )
            trend.write_formula(
                row,
                4,
                f'=IF(OR(F{row + 1}<>"yes",B{row + 1}=0),"",D{row + 1}/ABS(B{row + 1}))',
                self.f["pct"],
                ((av - pv) / abs(pv)) if (p <= last_closed and pv) else "",
            )
            trend.write(row, 5, "yes" if p <= last_closed else "no", self.f["text"])

    def _commitments(self, ws) -> None:
        heads = [
            "PO",
            "Line",
            "Line key",
            "Vendor",
            "Status",
            "Need by",
            "Ordered",
            "Posted",
            "Pending",
            "Open",
            "Released",
            "Overrun",
            "Check (should be 0)",
            "Linkage",
        ]
        ws.write(
            0, 0, "Purchase orders: where every ordered dollar is", self.f["title"]
        )
        ws.write(
            1,
            0,
            "Ordered = posted + pending + open + released - overrun. Open commitments are valued at the last closed period's exchange rate.",
            self.f["sub"],
        )
        self._header(
            ws, 3, heads, [11, 6, 26, 22, 9, 10, 13, 13, 13, 13, 12, 12, 14, 16]
        )
        for i, c in enumerate(self.r["commitments"]):
            row = 4 + i
            vals = [
                c["po_number"],
                c["po_line"],
                c["key"].replace(" | ", " · "),
                c["vendor"],
                c["status"],
                c["need_by"] or "",
            ]
            for col, v in enumerate(vals):
                ws.write(row, col, v, self.f["text"])
            for col, key in (
                (6, "ordered"),
                (7, "posted"),
                (8, "pending"),
                (9, "open_amount"),
                (10, "released"),
                (11, "overrun"),
            ):
                ws.write_number(row, col, round(c[key], 2), self.f["num"])
            r1 = row + 1
            check = round(
                round(c["ordered"], 2)
                - round(c["posted"], 2)
                - round(c["pending"], 2)
                - round(c["open_amount"], 2)
                - round(c["released"], 2)
                + round(c["overrun"], 2),
                2,
            )
            ws.write_formula(
                row,
                12,
                f"=ROUND(G{r1}-H{r1}-I{r1}-J{r1}-K{r1}+L{r1},2)",
                self.f["num"],
                check,
            )
            ws.write(row, 13, c["link"], self.f["text"])
        if not self.r["commitments"]:
            ws.write(4, 0, "No purchase orders were provided.", self.f["sub"])

    def _invoices(self, ws) -> None:
        heads = [
            "Invoice",
            "PO",
            "Line key",
            "Vendor",
            "Invoice date",
            "Amount",
            "Status",
            "In GL",
            "Days waiting",
        ]
        ws.write(0, 0, "Invoices and whether each has reached the GL", self.f["title"])
        ws.write(
            1,
            0,
            "Invoices not yet in the GL are pending: counted once, as pending, not as actuals. Unknown means the file could not show it either way.",
            self.f["sub"],
        )
        self._header(ws, 3, heads, [14, 11, 26, 22, 12, 13, 11, 8, 11])
        for i, v in enumerate(
            sorted(
                self.r["invoices"],
                key=lambda x: (x["posted"] is not False, -abs(x["amount"])),
            )
        ):
            row = 4 + i
            state = (
                "unknown" if v["posted"] is None else ("yes" if v["posted"] else "no")
            )
            vals = [
                v["invoice_number"],
                v["po_number"],
                v["key"].replace(" | ", " · "),
                v["vendor"],
                v["invoice_date"] or "",
            ]
            for col, x in enumerate(vals):
                ws.write(row, col, x, self.f["text"])
            ws.write_number(row, 5, round(v["amount"], 2), self.f["num"])
            ws.write(row, 6, v["status"], self.f["text"])
            ws.write(row, 7, state, self.f["text"])
            if v["days_unposted"] is not None:
                ws.write_number(row, 8, v["days_unposted"], self.f["heads"])
        if not self.r["invoices"]:
            ws.write(4, 0, "No invoice file was provided.", self.f["sub"])

    def _unplanned(self, ws) -> None:
        heads = [g.replace("_", " ").title() for g in self.r["grain"]] + [
            "Source value with no plan",
            "Actual YTD",
        ]
        ws.write(0, 0, "Actuals with no plan line", self.f["title"])
        ws.write(
            1,
            0,
            "Included in every total. Map them to a plan line (hierarchy) or confirm they are truly unbudgeted.",
            self.f["sub"],
        )
        self._header(ws, 3, heads, [18] * len(self.r["grain"]) + [30, 14])
        for i, u in enumerate(self.r["unplanned"]):
            row = 4 + i
            for c, d in enumerate(self.r["grain"]):
                ws.write(row, c, u["keys"].get(d, ""), self.f["text"])
            ws.write(row, len(self.r["grain"]), u["source_value"], self.f["text"])
            ws.write_number(
                row, len(self.r["grain"]) + 1, round(u["actual_ytd"], 2), self.f["num"]
            )
        if not self.r["unplanned"]:
            ws.write(4, 0, "Every actual maps to a plan line.", self.f["sub"])

    def _headcount(self, ws) -> None:
        ws.write(0, 0, "Headcount: plan and actual heads by month", self.f["title"])
        ws.write(
            1,
            0,
            "Heads are a point-in-time count. Compare a single month; never add months together.",
            self.f["sub"],
        )
        heads = [
            "Group",
            "Period",
            "Plan heads",
            "Actual heads",
            "Variance",
            "Variance %",
            "Open reqs",
            "Actual + reqs - plan",
        ]
        self._header(ws, 3, heads, [24, 10, 11, 12, 10, 11, 10, 18])
        last = self.r["window"]["last_closed"]
        rows = sorted(self.r["headcount"], key=lambda h: (h["key"], h["period"]))
        for i, h in enumerate(rows):
            row = 4 + i
            r1 = row + 1
            ws.write(row, 0, " · ".join(h["keys"].values()), self.f["text"])
            ws.write(row, 1, h["period"], self.f["text"])
            ws.write_number(row, 2, h["plan"], self.f["heads"])
            if h["period"] <= last:
                ws.write_number(row, 3, h["actual"], self.f["heads"])
                ws.write_formula(
                    row, 4, f"=D{r1}-C{r1}", self.f["heads"], h["actual"] - h["plan"]
                )
                ws.write_formula(
                    row,
                    5,
                    f'=IF(C{r1}=0,"",E{r1}/C{r1})',
                    self.f["pct"],
                    ((h["actual"] - h["plan"]) / h["plan"]) if h["plan"] else "",
                )
                if h["open_reqs"] is not None:
                    ws.write_number(row, 6, h["open_reqs"], self.f["heads"])
                    ws.write_formula(
                        row,
                        7,
                        f"=D{r1}+G{r1}-C{r1}",
                        self.f["heads"],
                        h["actual"] + h["open_reqs"] - h["plan"],
                    )
        if not rows:
            ws.write(4, 0, "No headcount file was provided.", self.f["sub"])

    def _tieout(self, ws) -> None:
        ws.write(0, 0, "Tie-out checks", self.f["title"])
        self._header(
            ws,
            2,
            ["Check", "Left", "Right", "Difference", "Result", "What it proves"],
            [44, 15, 15, 12, 8, 90],
        )
        row = 3
        for p in self.r["proof"]:
            ws.write(row, 0, p["name"], self.f["text"])
            ws.write_number(row, 1, round(p["left"], 2), self.f["num"])
            ws.write_number(row, 2, round(p["right"], 2), self.f["num"])
            ws.write_formula(
                row,
                3,
                f"=ROUND(B{row + 1}-C{row + 1},2)",
                self.f["num"],
                round(round(p["left"], 2) - round(p["right"], 2), 2),
            )
            ws.write(
                row,
                4,
                "PASS" if p["passed"] else "FAIL",
                self.f["pass"] if p["passed"] else self.f["fail"],
            )
            ws.write(row, 5, p["explanation"], self.f["wrap"])
            row += 1
        row += 1
        ws.write(row, 0, "Source walk", self.f["label"])
        row += 1
        for t in self.r["tie_out"]:
            ws.write(row, 0, f"{t['source']}: {t['label']}", self.f["text"])
            ws.write_number(row, 1, round(t["amount"], 2), self.f["num"])
            ws.write(row, 5, t.get("note", ""), self.f["sub"])
            row += 1
        row += 1
        ws.write(row, 0, "Findings", self.f["label"])
        row += 1
        for fd in self.r["findings"]:
            ws.write(
                row,
                0,
                f"[{fd['severity']}] {fd['code']}",
                self.f["fail"] if fd["severity"] == "error" else self.f["text"],
            )
            if fd.get("amount"):
                ws.write_number(row, 1, round(fd["amount"], 2), self.f["num"])
            ws.write(row, 5, fd["message"], self.f["wrap"])
            row += 1

    def _fx(self, ws) -> None:
        ws.write(
            0,
            0,
            f"Exchange rates used (to {self.r['reporting_currency']})",
            self.f["title"],
        )
        self._header(ws, 2, ["Currency", "Period", "Rate", "Basis"], [10, 10, 14, 22])
        for i, x in enumerate(self.r["fx_used"]):
            ws.write(3 + i, 0, x["currency"], self.f["text"])
            ws.write(3 + i, 1, x["period"], self.f["text"])
            ws.write_number(3 + i, 2, float(x["rate"]), self.f["rate"])
            ws.write(3 + i, 3, x["basis"], self.f["text"])
        if not self.r["fx_used"]:
            ws.write(
                3,
                0,
                f"Every row is already in {self.r['reporting_currency']}.",
                self.f["sub"],
            )

    def _method(self, ws) -> None:
        r = self.r
        rules = r["spec"].get("rules", {})
        ws.set_column(0, 0, 34)
        ws.set_column(1, 1, 110)
        ws.write(0, 0, "Method and settings", self.f["title"])
        rows = [
            (
                "Grain",
                ", ".join(r["grain"])
                + " (the plan's own level of detail; actuals roll up to it)",
            ),
            (
                "Plan year",
                f"{r['window']['horizon_start']} to {r['window']['horizon_end']}",
            ),
            ("Last closed period", r["window"]["last_closed"]),
            ("As of", r["window"]["as_of_date"]),
            (
                "Reporting currency",
                r["reporting_currency"]
                + ". Each row converts at its own period's rate; open POs at the last closed period's rate.",
            ),
            ("Sign convention", r["sign_convention"]),
            (
                "Outstanding",
                "Pending invoices (approved, not yet in the GL) plus open purchase orders. Available = full-year plan - actuals - pending - open.",
            ),
            ("Commitment linkage", f"{r['linkage']['method']}: {r['linkage']['note']}"),
            (
                "Materiality floor",
                f"{money(self.s, r['totals']['materiality_ytd'])} year to date, {money(self.s, r['totals']['materiality_cur'])} for the month"
                + (
                    " (set by the user)."
                    if rules.get("materiality_amount")
                    else f" (default: {rules.get('materiality_share', 0.005) * 100:.1f}% of gross plan, rounded down to two significant figures)."
                ),
            ),
            (
                "Relative threshold",
                f"{rules.get('variance_pct', 0.1) * 100:.0f}% of plan.",
            ),
            (
                "Statistical screen",
                f"Robust (median and median absolute deviation) z-score beyond {rules.get('z_threshold', 3.5)}: the month against the line's own prior months (at least {rules.get('min_history', 6)}), and the size-scaled variance against the other lines.",
            ),
            (
                "Inspect or watch",
                "Inspect: material and at least one more test (relative, statistical, committed past budget, no plan), or a document issue above the month floor. Watch: one test only, or an offsetting timing pattern.",
            ),
            (
                "Timing",
                f"A month's variance that reverses at least {100 - rules.get('timing_offset_share', 0.25) * 100:.0f}% of the prior {rules.get('timing_window', 2)} months' variance is marked likely timing.",
            ),
            (
                "Documents",
                f"Stale PO: open more than {rules.get('stale_commitment_days', 90)} days past need-by. Unposted invoice: waiting more than {rules.get('unposted_invoice_days', 30)} days. Possible duplicate: same vendor and amount within {rules.get('duplicate_window_days', 7)} days.",
            ),
            (
                "Headcount",
                "Compared at the last closed month only. Heads are never summed across months.",
            ),
            (
                "Assumptions",
                "; ".join(r["spec"].get("assumptions") or []) or "None stated.",
            ),
            ("Data notice", r.get("data_notice") or "None."),
            ("Engine", f"run_reconciliation.py {r['engine_version']}"),
        ]
        for i, (k, v) in enumerate(rows):
            ws.write(2 + i, 0, k, self.f["label"])
            ws.write(2 + i, 1, v, self.f["wrap"])

    def _summary(self, ws, sums: dict) -> None:
        r = self.r
        ws.set_column(0, 0, 34)
        ws.set_column(1, 1, 16)
        ws.set_column(2, 2, 90)
        ws.write(0, 0, r["name"], self.f["title"])
        if r.get("data_notice"):
            ws.merge_range(3, 0, 3, 2, r["data_notice"], self.f["fail"])
        ws.write(
            1,
            0,
            f"Through {r['window']['last_closed']} | {r['reporting_currency']} | as of {r['window']['as_of_date']}",
            self.f["sub"],
        )
        ws.merge_range(2, 0, 2, 2, HeadlineWriter(r, False).write(), self.f["wrap"])
        ws.set_row(2, 42)
        items = [
            (
                "Plan, year to date",
                "plan_ytd",
                "Sum of the plan for the closed months.",
            ),
            (
                "Actual, year to date",
                "actual_ytd",
                "GL actuals for the closed months, on every line including unplanned ones.",
            ),
            (
                "Variance, year to date",
                "var_ytd",
                "Actual minus plan. Positive = over plan.",
            ),
            ("Full-year plan", "plan_fy", "The whole plan year."),
            ("Pending invoices", "pending", "Approved invoices not yet in the GL."),
            ("Open purchase orders", "open", "Ordered and not yet invoiced or posted."),
            ("Committed", "committed", "Actual + pending + open."),
            (
                "Available",
                "available",
                "Full-year plan minus committed. Negative = committed beyond budget.",
            ),
        ]
        self._header(ws, 4, ["Measure", "Amount", "Definition"], [34, 16, 90])
        for i, (label, key, note) in enumerate(items):
            row = 5 + i
            ws.write(row, 0, label, self.f["text"])
            value = self.rounded_totals["open_commitments" if key == "open" else key]
            ws.write_formula(row, 1, f"={sums[key]}", self.f["num"], round(value, 2))
            ws.write(row, 2, note, self.f["sub"])
        row = 5 + len(items) + 1
        ws.write(row, 0, "Variance %, year to date", self.f["text"])
        rt = self.rounded_totals
        ws.write_formula(
            row,
            1,
            '=IF(B6=0,"",B8/ABS(B6))',
            self.f["pct"],
            (rt["var_ytd"] / abs(rt["plan_ytd"])) if rt["plan_ytd"] else "",
        )
        row += 2
        ws.write(row, 0, "Flags", self.f["label"])
        ws.write(row + 1, 0, "Inspect", self.f["text"])
        ws.write_number(
            row + 1,
            1,
            inspect_items(r),
            self.f["heads"],
        )
        ws.write(row + 2, 0, "Watch", self.f["text"])
        ws.write_formula(
            row + 2,
            1,
            '=COUNTIF(Inspect!B:B,"watch")',
            self.f["heads"],
            sum(1 for f in r["flags"] + r["headcount_flags"] if f["tier"] == "watch"),
        )
        row += 4
        ws.write(row, 0, "Tie-out", self.f["label"])
        for i, p in enumerate(r["proof"]):
            ws.write(row + 1 + i, 0, p["name"], self.f["text"])
            ws.write(
                row + 1 + i,
                1,
                "PASS" if p["passed"] else "FAIL",
                self.f["pass"] if p["passed"] else self.f["fail"],
            )
        row += 2 + len(r["proof"])
        ws.write(row, 0, "Sheets", self.f["label"])
        guide = [
            (
                "Inspect",
                "The ranked items to look at, with room for owner, status, and notes.",
            ),
            (
                "Lines",
                "Every line at the plan's grain with live variance, committed and available formulas.",
            ),
            (
                "Monthly / Trend",
                "Plan and actual per line and month, and the monthly totals.",
            ),
            ("Commitments / Invoices", "Where each ordered and invoiced dollar sits."),
            ("Unplanned", "Actuals with no plan line."),
            ("Headcount", "Plan and actual heads."),
            ("Tie-out", "The proofs, the source walk, and every finding."),
            ("FX rates", "Every rate used and whether it was the period's own."),
            ("Method", "Settings, thresholds and definitions."),
        ]
        for i, (k, v) in enumerate(guide):
            ws.write(row + 1 + i, 0, k, self.f["text"])
            ws.write(row + 1 + i, 2, v, self.f["sub"])
        ws.activate()
