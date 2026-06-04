"""Create a manual-labeling CSV from a raw Reddit scrape.

The raw scrape is kept as an audit copy in data/raw. This script creates a
separate file under data/labeling with columns meant for human annotation.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path


LABEL_CHOICES = {
    "low_risk_diy",
    "medium_risk_call_pro",
    "urgent_safety_risk",
    "exclude_unclear",
}


def newest_raw_csv(raw_dir: Path) -> Path:
    files = sorted(
        [
            path
            for pattern in ["reddit_diy_repair_posts_*.csv", "reddit_home_repair_posts_*.csv"]
            for path in raw_dir.glob(pattern)
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(f"No raw CSV files found in {raw_dir}")
    return files[0]


def prepare_labeling_file(input_path: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", newline="", encoding="utf-8") as input_handle:
        reader = csv.DictReader(input_handle)
        if not reader.fieldnames:
            raise ValueError(f"{input_path} has no header row")

        fieldnames = list(reader.fieldnames)
        for column in ["label", "label_status", "label_notes"]:
            if column not in fieldnames:
                fieldnames.append(column)

        rows = []
        for row in reader:
            row["label"] = row.get("label", "")
            row["label_status"] = row.get("label_status") or "unlabeled"
            row["label_notes"] = row.get("label_notes", "")
            rows.append(row)

    with output_path.open("w", newline="", encoding="utf-8") as output_handle:
        writer = csv.DictWriter(output_handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a human-labeling CSV from the newest raw scrape."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Raw CSV to convert. Defaults to the newest CSV in data/raw.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory to search when --input is not provided.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output labeling CSV. Defaults to data/labeling/diy_repair_labeling_<timestamp>.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input or newest_raw_csv(args.raw_dir)
    output_path = args.output
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path("data/labeling") / f"diy_repair_labeling_{timestamp}.csv"

    row_count = prepare_labeling_file(input_path=input_path, output_path=output_path)
    print(f"Prepared {row_count} rows for labeling")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print("Use label values: " + ", ".join(sorted(LABEL_CHOICES)))


if __name__ == "__main__":
    main()
