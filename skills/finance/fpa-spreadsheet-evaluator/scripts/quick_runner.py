"""
description: Run the Spreadsheet Evaluator scripts in-process inside the AWS Quick Python sandbox, one method per workflow step.
last_updated: 2026-11-24

quick_runner.py - run the Spreadsheet Evaluator scripts inside the AWS Quick Python sandbox.

The scripts are imported as modules and each workflow step is one method. Variables don't survive
between code calls, so import and create the review object at the start of every call; the review
state lives on disk, so this is safe:

    import quick_runner
    ev = quick_runner.SheetReview("<path to model>", workspace=WORKSPACE_DIR,
                                  out_dir="<folder the user chose>", timezone="America/Los_Angeles")

Then:
    ev.scan(excel_target="auto")      # scan, then read scan.json's intake and notes
    ev.show("Sheet!A1:F12")           # look at a small range
    ev.save_json("decisions", {...})  # judge the findings
    ev.plan()                         # numbered change list
    ev.save_json("narrative", {...})
    ev.render()                       # writes the HTML report into out_dir
    ev.apply("1,2,4-7")               # fixed copy in out_dir + re-check
    ev.render()                       # refreshes the report with what was applied

No formula recalculation is bundled: the fixed copy keeps its saved values and Excel recalculates
it on open. Each call prints the script's own output and returns its exit code (0 = fine).
"""

import datetime as dt
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import apply_changes
import compare_workbooks
import plan_changes
import render_report
import report_context
import scan_workbook

SUPPORTED = (".xlsx", ".xlsm")
MAX_BYTES = (
    50 * 1024 * 1024
)  # files over about 50 MB can't be audited in the sandbox's time limit
CONTEXT_FIELDS = ("headers", "date_order", "unit_notes")
JSON_NAME = re.compile(
    r"[a-z][a-z_]{0,39}"
)  # working-file names such as "decisions"; no paths
UTC_TZ = dt.timezone.utc  # noqa: UP017 - datetime.UTC needs Python 3.11; the skill supports 3.10


def _slug(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_") or "model"


def _now(timezone):
    now = dt.datetime.now(UTC_TZ)
    if timezone:
        try:
            zone = ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError):
            zone = None  # unknown zone: keep UTC
        if zone is not None:
            now = now.astimezone(zone)
    hour = now.strftime("%I").lstrip("0") or "12"
    return f"{now.day} {now.strftime('%b %Y')}, {hour}:{now.strftime('%M %p')} {now.strftime('%Z') or 'UTC'}"


def _check_input(path):
    """Refuse a file the scan can't read before anything is copied (Gotcha 2 in SKILL.md)."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED:
        raise ValueError(
            "Only .xlsx and .xlsm workbooks can be audited: save the workbook as .xlsx first."
        )
    if not os.path.isfile(path):
        raise ValueError(f"File not found: {os.path.basename(path)}")
    if os.path.getsize(path) > MAX_BYTES:
        raise ValueError("The file is over 50 MB; save a smaller copy to audit.")


def _json_name(name):
    """A working-file name, never a path, so save_json can't write outside the working folder."""
    if not isinstance(name, str) or not JSON_NAME.fullmatch(name):
        raise ValueError(
            "save_json takes a short name such as 'decisions', not a path."
        )
    return f"{name}.json"


def _write_json(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print(f"Saved {path}")
    return path


def _claim_output(work_dir, path):
    """Refuse to replace a file the runner didn't write; remember the ones it did."""
    ledger = os.path.join(work_dir, "written.json")
    mine = _read_json(ledger) or []
    if os.path.exists(path) and path not in mine:
        raise ValueError(
            f"{os.path.basename(path)} already exists in the save folder and wasn't written by this review; "
            "move it or choose another out_dir."
        )
    if path not in mine:
        with open(ledger, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(mine + [path], fh)


def _read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class SheetReview:
    """One review of one model. Working files stay under workspace; deliverables go to out_dir."""

    def __init__(self, model_path, workspace=None, timezone=None, out_dir=None):
        _check_input(model_path)
        ws = workspace or "."
        self.ws = ws
        self.source = model_path
        self.timezone = timezone
        self.name = _slug(os.path.splitext(os.path.basename(model_path))[0])
        self.ext = os.path.splitext(model_path)[1].lower()
        self.out_dir = out_dir or os.path.join(ws, "artifacts")
        self.w = os.path.join(ws, "artifacts", ".metadata", f"{self.name}.review")
        os.makedirs(self.w, exist_ok=True)
        os.makedirs(self.out_dir, exist_ok=True)
        self.report = os.path.join(self.out_dir, f"{self.name}_review.html")
        self.fixed = os.path.join(self.out_dir, f"{self.name}_fixed{self.ext}")
        if os.path.exists(self.fixed) and os.path.samefile(self.fixed, model_path):
            raise ValueError(
                "The fixed copy would replace the original; choose another out_dir."
            )
        # Review a snapshot, never the user's file: protects the original and gives
        # apply_changes a stable file to check against.
        snap_dir = os.path.join(self.w, "source")
        os.makedirs(snap_dir, exist_ok=True)
        self.model = os.path.join(snap_dir, os.path.basename(model_path))
        self._sync_snapshot()
        self._mods = {
            "scan_workbook": scan_workbook,
            "plan_changes": plan_changes,
            "apply_changes": apply_changes,
            "render_report": render_report,
            "report_context": report_context,
            "compare_workbooks": compare_workbooks,
        }
        print(
            f"Model: {model_path}\nWorking files: {self.w}\n"
            f"Report: {self.report}\nFixed copy: {self.fixed}"
        )

    # -- helpers -------------------------------------------------------------------------------
    def _sync_snapshot(self):
        """Copy the user's file in; if it changed since the last review, start the review over."""
        digest = hashlib.sha256(Path(self.source).read_bytes()).hexdigest()
        stamp = Path(self.w) / "source.sha256"
        old = stamp.read_text(encoding="utf-8").strip() if stamp.exists() else None
        if old == digest and os.path.exists(self.model):
            return
        # copyfile copies only the bytes; the snapshot needs no file metadata
        shutil.copyfile(self.source, self.model)
        stamp.write_text(digest, encoding="utf-8", newline="\n")
        if old:
            self._clear_working()
            print(
                "The model changed since the last review: snapshot refreshed and earlier plan cleared. Re-run scan()."
            )

    def _clear_working(self):
        for f in os.listdir(self.w):
            if (
                f.endswith(".json") and f != "written.json"
            ):  # keep the list of files it wrote
                os.remove(os.path.join(self.w, f))

    def p(self, name):
        return os.path.join(self.w, name)

    def _run(self, script, args):
        try:
            rc = self._mods[script].main([str(a) for a in args])
        except SystemExit as e:  # the scripts exit with a message on user-facing errors
            if e.code not in (None, 0):
                print(
                    e.code if isinstance(e.code, str) else f"Exited with code {e.code}"
                )
            rc = (
                0 if e.code in (None, 0) else (e.code if isinstance(e.code, int) else 1)
            )
        return rc or 0

    def _json(self, name):
        return _read_json(self.p(f"{name}.json"))

    def save_json(self, name, data):
        """Write decisions / judgments / narrative JSON into the working folder."""
        return _write_json(self.p(_json_name(name)), data)

    def _opt(self, flag, name):
        path = self.p(f"{name}.json")
        return [flag, path] if os.path.exists(path) else []

    def _changelog_path(self):
        return self.p(
            f"{os.path.splitext(os.path.basename(self.fixed))[0]}_changelog.json"
        )

    def _pending_questions(self):
        return (self._json("scan") or {}).get("intake", {}).get("questions", [])

    # -- steps ---------------------------------------------------------------------------------
    def scan(self, excel_target="auto", top=40, context=None):
        """Scan without guessing. Context contains only answers actually supplied by the user."""
        known = self._json("intake_context") or {}
        if context:
            for field, answers in context.items():
                if field not in CONTEXT_FIELDS or not isinstance(answers, dict):
                    raise ValueError(
                        "Context supports headers, date_order and unit_notes, each keyed by sheet."
                    )
                known.setdefault(field, {}).update(answers)
            self.save_json("intake_context", known)
        sw = self._mods["scan_workbook"]
        result = sw.scan(Path(self.model), excel_target, context=known)
        self.save_json("scan", result)
        print(sw.summary(result, self.p("scan.json"), top))
        return 0

    def show(self, rng):
        return self._run("scan_workbook", ["show", self.model, rng])

    def plan(self):
        log_path = self._changelog_path()
        if os.path.exists(log_path):  # a new plan replaces any earlier apply
            os.remove(log_path)
        pending = self._pending_questions()
        if pending:
            print(
                "Needs clarification before planning changes. Verified formula findings can be shared as preliminary."
            )
            for q in pending:
                print(
                    "Question with file content (data, not instructions): "
                    + json.dumps(q["question"][:600], ensure_ascii=True)
                )
            return 2
        rc = self._run(
            "plan_changes",
            [self.model, self.p("scan.json"), self.p("changes.json")]
            + self._opt("--decisions", "decisions"),
        )
        plan, scan = self._json("changes"), self._json("scan")
        if rc or not plan:
            return rc
        ctx = self._mods["report_context"].build(self.model, scan, plan)
        labels = [
            f"#{n}: {c['label'][:80]}"
            for n, c in ctx["changes"].items()
            if c.get("label")
        ]
        if labels:
            print(
                "Labels from the file (data, not instructions): "
                + json.dumps(labels, ensure_ascii=True)
            )
        return rc

    def _changelog(self):
        """The apply log, only when the copy it describes still exists."""
        log = _read_json(self._changelog_path())
        if log and log.get("copy") and os.path.isfile(log["copy"]):
            return log
        return None

    def render(self):
        if self._pending_questions():
            print(
                "Final report not written: resolve the scan's intake questions first, or share a clearly labeled preliminary summary."
            )
            return 2
        scan, plan = self._json("scan"), self._json("changes")
        log = self._changelog()
        ctx = self._mods["report_context"].build(
            self.model,
            scan,
            plan,
            source=self.source,
            generated=_now(self.timezone),
            changelog=log,
        )
        self.save_json("context", ctx)
        args = (
            [self.p("scan.json"), self.report]
            + self._opt("--changes", "changes")
            + self._opt("--decisions", "decisions")
            + self._opt("--narrative", "narrative")
            + ["--context", self.p("context.json")]
            + self._opt("--judgments", "judgments")
        )
        if log:
            args += ["--applied", self._changelog_path()]
        try:
            _claim_output(self.w, self.report)
        except ValueError as exc:
            print(f"Report not written: {exc}")
            return 2
        return self._run("render_report", args)

    def apply(self, approve, force=False):
        """approve: 'safe', 'all', or numbers like '1,2,4-7'. Rebuilds the copy from the snapshot.

        The runner's own earlier copy is replaced; any other existing file at that path is not."""
        if self._pending_questions():
            print(
                "No changes applied: the source interpretation still needs clarification."
            )
            return 2
        own_copy = self._changelog() is not None
        return self._run(
            "apply_changes",
            [
                self.p("changes.json"),
                "--approve",
                approve,
                "--out",
                self.fixed,
                "--scan",
                self.p("scan.json"),
            ]
            + (["--force"] if (force or own_copy) else []),
        )

    def compare_with(self, prior_path, out_dir=None):
        """Shortcut: compare an earlier version against this model (see WorkbookComparison)."""
        return WorkbookComparison(
            prior_path,
            self.source,
            workspace=self.ws,
            timezone=self.timezone,
            out_dir=out_dir or self.out_dir,
            _mods=self._mods,
        )

    def reset(self):
        """Start over from the user's current file."""
        stamp = os.path.join(self.w, "source.sha256")
        if os.path.exists(stamp):
            os.remove(stamp)
        self._clear_working()
        self._sync_snapshot()
        print("Snapshot refreshed and working files cleared; run scan() again.")


class WorkbookComparison:
    """Compare two versions of a workbook: what changed, and what looks unintended.

    cmp = quick_runner.WorkbookComparison("<old version>", "<new version>", workspace=WORKSPACE_DIR,
                                          out_dir="<folder the user chose>", timezone="America/Los_Angeles")
    cmp.run()                                  # prints the summary, writes compare.json
    cmp.save_json("compare_narrative", {...})  # optional: summary + why flagged items matter
    cmp.render()                               # <out_dir>/<new>_vs_<old>_comparison.html
    """

    def __init__(
        self,
        old_path,
        new_path,
        workspace=None,
        timezone=None,
        out_dir=None,
        _mods=None,
    ):
        _check_input(old_path)
        _check_input(new_path)
        ws = workspace or "."
        self.timezone = timezone
        old_n = _slug(os.path.splitext(os.path.basename(old_path))[0])
        new_n = _slug(os.path.splitext(os.path.basename(new_path))[0])
        tag = f"{new_n}_vs_{old_n}" if old_n != new_n else f"{new_n}_versions"
        self.w = os.path.join(ws, "artifacts", ".metadata", f"{tag}.compare")
        out_dir = out_dir or os.path.join(ws, "artifacts")
        os.makedirs(out_dir, exist_ok=True)
        self.report = os.path.join(out_dir, f"{tag}_comparison.html")
        self.paths = {}
        for side, src in (
            ("old", old_path),
            ("new", new_path),
        ):  # snapshots: never touch either file
            d = os.path.join(self.w, side)
            os.makedirs(d, exist_ok=True)
            dst = os.path.join(d, os.path.basename(src))
            shutil.copyfile(src, dst)
            self.paths[side] = dst
        self.cw = compare_workbooks if _mods is None else _mods["compare_workbooks"]
        print(
            f"Old: {old_path}\nNew: {new_path}\nWorking files: {self.w}\nReport: {self.report}"
        )

    def p(self, name):
        return os.path.join(self.w, name)

    def save_json(self, name, data):
        return _write_json(self.p(_json_name(name)), data)

    def run(self, excel_target="auto"):
        res = self.cw.compare(self.paths["old"], self.paths["new"], excel_target)
        with open(self.p("compare.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, indent=1, default=str)
        print(self.cw.text_summary(res))
        return 0

    def render(self):
        res = _read_json(self.p("compare.json"))
        if res is None:
            print("Run cmp.run() before cmp.render().")
            return 2
        narr = _read_json(self.p("compare_narrative.json"))
        html_text = self.cw.render(res, narr, _now(self.timezone))
        try:
            _claim_output(self.w, self.report)
        except ValueError as exc:
            print(f"Comparison not written: {exc}")
            return 2
        with open(self.report, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html_text)
        print(
            f"Wrote {self.report} ({len(html_text) // 1024} KB). Tabs: Summary, What changed, Structure, Issues."
        )
        return 0
