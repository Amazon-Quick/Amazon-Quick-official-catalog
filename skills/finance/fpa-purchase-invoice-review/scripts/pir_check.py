"""
description: Run the deterministic purchase and invoice review checks (profile, coding, budget, contract, price, approval, invoice, justification, combine, summary, all) and return JSON results.
last_updated: 2026-11-24

Purchase and invoice review: deterministic checks (Python standard library only).

Subcommands: profile, coding, budget, contract, price, approval, invoice,
             justification, combine, summary, all.

Each subcommand accepts --input <file or -> containing a whole pasted message.
Columns are fuzzy-mapped by pir_columns so req_id/amount/cc/etc. all work.
A row whose field count differs from its header is returned as a clarification question.
Missing period column -> assumed_single_period:true in output.

This module is the command-line and in-process entry point only. Each check lives in its
own module (pir_coding, pir_budget, pir_contract, pir_price, pir_approval, pir_invoice,
pir_justification), with shared parsing in pir_tables and pir_values, state in pir_state,
the batch summary in pir_summary and the `all` command in pir_all.

Output is JSON on stdout, keys sorted, money as strings with 2 decimals, so the
same inputs always give byte-identical output. Every finding carries the rule id,
the number, the source (file:line) and the $ at stake. Labels: every result is
"script-computed"; anything the model adds afterwards must be labeled
"model-computed".

Severity -> suggested verdict (the model may only make it stricter, with a reason):
  HOLD -> Hold, SEND_BACK -> Send back, CONDITION -> Approve with conditions,
  INFO -> no effect. No finding -> Approve.
"""

import argparse
import contextlib
import io
import json
import sys

from pir_all import cmd_all
from pir_approval import cmd_approval
from pir_budget import cmd_budget
from pir_coding import cmd_coding
from pir_contract import cmd_contract
from pir_invoice import cmd_invoice
from pir_justification import cmd_justification
from pir_price import cmd_price
from pir_profile import cmd_profile
from pir_state import (
    _EXCLUDED_ROWS,
    _IGNORED_TABLES,
    _MAPPED_COLS,
    _STATE,
    _TABLE_CACHE,
    INPUTS,
    ClarificationNeeded,
    _emit,
    _intake_result,
)
from pir_summary import cmd_combine, cmd_summary
from pir_tables import normalize_header


class _ParserExit(Exception):
    """argparse wanted to exit (--help or bad arguments). Raised instead of sys.exit, which can end Quick's
    sandbox worker. args[0] is the exit status."""


class _NoExitParser(argparse.ArgumentParser):
    """ArgumentParser that never calls sys.exit: help and errors raise _ParserExit instead."""

    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, sys.stderr)
        raise _ParserExit(status)

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None, quiet=False):
    p = _NoExitParser(prog="pir_check.py", description=__doc__.splitlines()[0])
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("profile")
    s.add_argument("--profile")
    s.add_argument("--modules", required=True)

    s = sp.add_parser("coding")
    s.add_argument("--lines")
    s.add_argument("--prior")
    s.add_argument("--capex-threshold", default=None)
    s.add_argument("--life-months", default="12")
    s.add_argument("--materiality", default=None)
    s.add_argument("--project-required", action="store_true")
    s.add_argument(
        "--input",
        default=None,
        metavar="FILE",
        help="Whole pasted message file; tables are auto-detected",
    )

    s = sp.add_parser("budget")
    s.add_argument("--budget")
    s.add_argument("--actuals")
    s.add_argument("--commitments")
    s.add_argument("--requests")
    s.add_argument("--grain", default="cost_center,account")
    s.add_argument(
        "--fiscal-start-month",
        type=int,
        choices=range(1, 13),
        default=1,
        metavar="1-12",
    )
    s.add_argument("--as-of")
    s.add_argument("--stale-days", type=int, default=90)
    s.add_argument("--commit-statuses", default="open")
    s.add_argument("--input", default=None, metavar="FILE")

    s = sp.add_parser("contract")
    s.add_argument("--contract")
    s.add_argument("--pos")
    s.add_argument("--rates")
    s.add_argument("--change-orders")
    s.add_argument("--as-of")
    s.add_argument("--renewal-warn-days", type=int, default=90)
    s.add_argument("--input", default=None, metavar="FILE")

    s = sp.add_parser("price")
    s.add_argument("--lines")
    s.add_argument("--history")
    s.add_argument("--quotes")
    s.add_argument("--tolerance", default=None)
    s.add_argument("--quote-threshold", default=None)
    s.add_argument("--quotes-required", type=int, default=2)
    s.add_argument("--window-days", type=int, default=365)
    s.add_argument("--as-of")
    s.add_argument("--input", default=None, metavar="FILE")

    s = sp.add_parser("approval")
    s.add_argument("--requests")
    s.add_argument("--tiers", default=None)
    s.add_argument("--split-window-days", type=int, default=30)
    s.add_argument("--split-margin", default="0.15")
    s.add_argument("--addon-warn", default="0.15")
    s.add_argument("--input", default=None, metavar="FILE")

    s = sp.add_parser("invoice")
    s.add_argument("--invoices")
    s.add_argument("--po-lines")
    s.add_argument("--receipts")
    s.add_argument("--period-start")
    s.add_argument("--period-end")
    s.add_argument("--qty-tol", default="0")
    s.add_argument("--price-tol", default=None)
    s.add_argument("--dup-window-days", type=int, default=30)
    s.add_argument("--as-of")
    s.add_argument("--input", default=None, metavar="FILE")

    s = sp.add_parser("combine")
    s.add_argument(
        "--results",
        required=True,
        help="comma-separated JSON result files from earlier subcommands",
    )

    s = sp.add_parser("justification")
    s.add_argument("--requests")
    s.add_argument("--template-fields", default=None)
    s.add_argument("--input", default=None, metavar="FILE")

    s = sp.add_parser("summary")
    s.add_argument("--verdicts", required=True)
    s.add_argument("--items", required=True)

    s = sp.add_parser(
        "all",
        description="Run all applicable modules on one pasted message and return combined JSON.",
    )
    s.add_argument(
        "--input",
        required=True,
        metavar="FILE",
        help="Whole pasted message (Markdown tables and/or CSV blocks)",
    )
    s.add_argument(
        "--grain",
        default=None,
        help="Budget grain columns from the profile, for example cost_center,account",
    )
    s.add_argument(
        "--fiscal-start-month",
        type=int,
        choices=range(1, 13),
        default=None,
        metavar="1-12",
        help="First month of the fiscal year from the profile",
    )
    s.add_argument(
        "--tiers",
        default=None,
        help="Approval tier upper limits, comma-separated, for example 10000,50000",
    )
    s.add_argument("--period-start", default=None)
    s.add_argument("--period-end", default=None)
    s.add_argument(
        "--price-tol",
        default=None,
        help="Invoice unit-price tolerance against PO, for example 0.02",
    )
    s.add_argument("--qty-tol", default="0")
    s.add_argument("--capex-threshold", default=None)
    s.add_argument("--materiality", default=None)
    s.add_argument("--quote-threshold", default=None)
    s.add_argument("--quotes-required", type=int, default=2)
    s.add_argument(
        "--price-history-tol",
        default=None,
        help="Unit price against history median tolerance, for example 0.20",
    )
    s.add_argument(
        "--template-fields",
        default=None,
        help="CSV with one column 'element' (justification template)",
    )
    s.add_argument("--as-of", default=None)

    for subparser in sp.choices.values():
        subparser.add_argument(
            "--column-map",
            default="{}",
            help="JSON raw header to canonical field mappings confirmed by the user",
        )
        subparser.add_argument("--date-order", choices=["MDY", "DMY"], default=None)
    try:
        a = p.parse_args(argv)
    except _ParserExit as exc:
        if quiet:
            raise  # run() turns this into a help or error dict
        sys.exit(exc.args[0])  # command line only
    INPUTS.clear()
    _TABLE_CACHE.clear()
    _MAPPED_COLS.clear()
    _IGNORED_TABLES.clear()
    _EXCLUDED_ROWS.clear()
    column_map = json.loads(a.column_map)
    if not isinstance(column_map, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in column_map.items()
    ):
        raise ValueError("--column-map must be a JSON object of header to field names")
    _STATE["column_map"] = {
        normalize_header(k): normalize_header(v) for k, v in column_map.items()
    }
    _STATE["date_order"] = a.date_order
    _STATE.pop("notes", None)
    _STATE.pop("policy_candidates", None)
    _STATE["result"] = None
    _STATE["quiet"] = quiet
    try:
        {
            "profile": cmd_profile,
            "coding": cmd_coding,
            "budget": cmd_budget,
            "contract": cmd_contract,
            "price": cmd_price,
            "approval": cmd_approval,
            "invoice": cmd_invoice,
            "combine": cmd_combine,
            "justification": cmd_justification,
            "summary": cmd_summary,
            "all": cmd_all,
        }[a.cmd](a)
    except ClarificationNeeded as exc:
        _STATE["quiet"] = quiet
        _emit(_intake_result(exc))
    return _STATE["result"]


def run(*argv):
    """In-process entry point (AWS Quick run_python, notebooks, tests). Never prints.

    Call as run(["all", "--input", "msg.txt"]) or run("all", "--input", "msg.txt").
    Returns a JSON-serializable dict with "ok": True on success. Never raises SystemExit:
    argparse errors, missing files and other failures come back as
    {"ok": False, "error": "...", "argv": [...]}; "--help" comes back as {"ok": True, "help": "..."}.
    State is reset on every call.
    """
    if len(argv) == 1 and isinstance(argv[0], (list, tuple)):
        argv = tuple(argv[0])
    args = [str(x) for x in argv]
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            res = main(args, quiet=True)
    except (_ParserExit, SystemExit) as e:
        code = e.args[0] if isinstance(e, _ParserExit) else e.code
        if code in (None, 0):  # argparse --help: return the text, do not print it
            return {"ok": True, "help": out.getvalue(), "argv": args}
        msg = (
            code
            if isinstance(code, str)
            else (err.getvalue().strip() or f"exit status {code}")
        )
        return {"ok": False, "error": msg, "argv": args}
    except Exception as e:  # noqa: BLE001 - the in-process caller gets an error dict, not a traceback
        return {"ok": False, "error": repr(e), "argv": args}
    if not isinstance(res, dict):
        return {"ok": False, "error": "no result produced", "argv": args}
    res.setdefault("ok", True)
    return res
