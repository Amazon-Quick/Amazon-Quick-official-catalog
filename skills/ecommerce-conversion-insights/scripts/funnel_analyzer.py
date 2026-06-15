"""
Funnel Analyzer.

Loads funnel data from uploaded CSV or Excel files and returns
a standardized structure for analysis.

Usage:
    python funnel_analyzer.py --file-path PATH
                              --segments "device,geo,category"

Output:
    JSON to stdout with standardized funnel DataFrame structure:
    {
        "stages": [...],
        "data": [...],
        "metadata": {...}
    }
"""

import argparse
import json
import sys
from datetime import datetime

import pandas as pd


def load_file_data(file_path: str, segments: list[str]) -> dict:
    """Load funnel data from a CSV or Excel file."""
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    elif file_path.endswith((".xlsx", ".xls")):
        df = pd.read_excel(file_path)
    else:
        raise ValueError(
            f"Unsupported file format: {file_path}. Use .csv, .xlsx, or .xls"
        )

    col_mapping = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in (
            "stage_name",
            "stage",
            "funnel_stage",
            "step",
        ):
            col_mapping[col] = "stage"
        elif col_lower in (
            "visitors",
            "users",
            "sessions",
            "traffic",
        ):
            col_mapping[col] = "visitors"
        elif col_lower in (
            "conversions",
            "converted",
            "completed",
        ):
            col_mapping[col] = "conversions"
        elif col_lower in (
            "device",
            "device_type",
            "devicecategory",
            "device_category",
        ):
            col_mapping[col] = "device"
        elif col_lower in (
            "geo",
            "geography",
            "country",
            "region",
        ):
            col_mapping[col] = "geo"
        elif col_lower in (
            "category",
            "product_category",
            "item_category",
        ):
            col_mapping[col] = "category"
        elif col_lower in (
            "avg_order_value",
            "aov",
            "order_value",
        ):
            col_mapping[col] = "avg_order_value"

    df = df.rename(columns=col_mapping)

    required = {"stage", "visitors"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}. "
            "Expected: stage_name/stage, visitors/users/sessions"
        )

    stage_names = df["stage"].unique().tolist()
    results = []

    for _, row in df.iterrows():
        record = {
            "stage": row["stage"],
            "stage_order": stage_names.index(row["stage"]) + 1,
            "visitors": int(row["visitors"]),
            "events": int(row.get("conversions", row["visitors"])),
        }
        for seg in segments:
            if seg in df.columns:
                record[seg] = str(row[seg])
        if "avg_order_value" in df.columns:
            record["avg_order_value"] = float(row["avg_order_value"])
        results.append(record)

    return {
        "stages": stage_names,
        "data": results,
        "metadata": {
            "source": "uploaded_file",
            "file_path": file_path,
            "date_range": {"start": "N/A", "end": "N/A"},
            "segments": [s for s in segments if s in df.columns],
            "fetched_at": datetime.now().isoformat(),
            "row_count": len(df),
        },
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=("Load and standardize funnel data from CSV or Excel files")
    )
    parser.add_argument(
        "--file-path",
        required=True,
        help="Path to CSV or Excel funnel data file",
    )
    parser.add_argument(
        "--segments",
        default="device,geo,category",
        help="Comma-separated segment dimensions to extract",
    )

    args = parser.parse_args()
    segments = [s.strip() for s in args.segments.split(",")]

    try:
        result = load_file_data(args.file_path, segments)
        print(json.dumps(result, indent=2))
    except Exception as e:
        error_output = {
            "error": str(e),
            "troubleshooting": (
                "Verify file exists and contains required "
                "columns (stage_name, visitors). "
                "Supported formats: .csv, .xlsx, .xls"
            ),
        }
        print(json.dumps(error_output, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
