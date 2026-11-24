"""
description: Turn results.json from run_reconciliation.py into a single-page HTML report (budget walk, monthly plan versus actual, items needing inspection, variance by line, headcount, data confidence) and a detailed Excel workbook whose totals are live formulas over the line detail.
last_updated: 2026-11-24
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from pydantic import BaseModel
from report_html import HtmlReportBuilder
from report_workbook import WorkbookWriter


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
logger = logging.getLogger("create_report")


class ReportFiles(BaseModel):
    html_path: str
    xlsx_path: str


class ReportFacade:
    """Reads results.json and writes the HTML report and the workbook."""

    def __init__(self, results_path: Path, out_dir: Path, stem: str) -> None:
        self.results_path = results_path
        self.out_dir = out_dir
        self.stem = stem

    def create(self) -> ReportFiles:
        if (
            self.stem in {"", ".", ".."}
            or "/" in self.stem
            or "\\" in self.stem
            or Path(self.stem).name != self.stem
        ):
            raise ValueError("stem must be a file name without path separators")
        if not self.results_path.is_file():
            raise ValueError(f"Results file not found: {self.results_path}")
        result = json.loads(self.results_path.read_text(encoding="utf-8"))
        xlsx = self.out_dir / f"{self.stem}.xlsx"
        page = self.out_dir / f"{self.stem}.html"
        sources = {self.results_path.resolve()}
        if result.get("source_files"):
            sources.update(Path(p).resolve() for p in result["source_files"])
        else:
            # Older results did not record the source base directory.
            spec = result.get("spec", {})
            for source in [
                *spec.get("sources", {}).values(),
                *spec.get("hierarchies", []),
            ]:
                if source and source.get("path"):
                    path = Path(source["path"])
                    for base in (self.results_path.parent, self.out_dir, Path.cwd()):
                        sources.add((base / path).resolve())
        for output in (xlsx, page):
            if output.resolve().parent != self.out_dir.resolve():
                raise ValueError("Report output must stay inside out_dir")
            if output.resolve() in sources or (
                output.exists()
                and any(p.exists() and output.samefile(p) for p in sources)
            ):
                raise ValueError("Report output would overwrite a source file")
        self.out_dir.mkdir(parents=True, exist_ok=True)
        WorkbookWriter(result, str(xlsx)).write()
        page.write_text(
            HtmlReportBuilder(result, xlsx.name).build(), encoding="utf-8", newline="\n"
        )
        return ReportFiles(html_path=str(page), xlsx_path=str(xlsx))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the one-page HTML report and the detailed workbook from results.json."
    )
    parser.add_argument("--results", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--stem",
        default="budget-reconciliation",
        help="File name without extension for both outputs.",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as err:
        return 0 if err.code == 0 else 2
    try:
        files = ReportFacade(Path(args.results), Path(args.out_dir), args.stem).create()
    except (ValueError, OSError) as err:
        logger.error("Input problem: %s", err)
        return 2
    logger.info("Wrote %s", files.html_path)
    logger.info("Wrote %s", files.xlsx_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
