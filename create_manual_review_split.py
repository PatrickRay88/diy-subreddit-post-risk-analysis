"""Create a human-review set and weak-label training pool.

This script prevents circular evaluation by holding human-review rows out of the
weak-label training pool. The review set keeps auto-label metadata for auditing,
but humans enter their judgment in separate human_* columns.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path


TRAINING_LABELS = {
    "low_risk_diy",
    "medium_risk_call_pro",
    "urgent_safety_risk",
}

REVIEW_BUCKETS = [
    "low_risk_diy",
    "medium_risk_call_pro",
    "urgent_safety_risk",
    "needs_human_review",
]

DEFAULT_REVIEWERS = ["Patrick", "Sarah", "Max", "Manthan"]


def newest_csv(directory: Path, pattern: str) -> Path:
    files = sorted(
        directory.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} found in {directory}")
    return files[0]


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path} has no header row")
        return list(reader), list(reader.fieldnames)


def write_rows(rows: list[dict[str, str]], fieldnames: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def review_bucket(row: dict[str, str]) -> str:
    if row.get("needs_human_review") == "yes":
        return "needs_human_review"
    auto_label = row.get("auto_label")
    if auto_label in TRAINING_LABELS:
        return auto_label
    return "needs_human_review"


def stratified_review_sample(
    rows: list[dict[str, str]],
    review_size: int,
    seed: int,
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, str]]] = {bucket: [] for bucket in REVIEW_BUCKETS}
    for row in rows:
        buckets[review_bucket(row)].append(row)

    for bucket_rows in buckets.values():
        rng.shuffle(bucket_rows)

    selected: list[dict[str, str]] = []
    selected_ids: set[str] = set()
    base_target = max(1, review_size // len(REVIEW_BUCKETS))

    for bucket in REVIEW_BUCKETS:
        for row in buckets[bucket][:base_target]:
            selected.append(row)
            selected_ids.add(row.get("reddit_id", ""))

    remaining = [
        row
        for bucket in REVIEW_BUCKETS
        for row in buckets[bucket]
        if row.get("reddit_id", "") not in selected_ids
    ]
    rng.shuffle(remaining)

    for row in remaining:
        if len(selected) >= review_size:
            break
        selected.append(row)
        selected_ids.add(row.get("reddit_id", ""))

    rng.shuffle(selected)
    return selected[:review_size]


def assign_reviewers(
    rows: list[dict[str, str]],
    reviewers: list[str],
    seed: int,
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    reviewer_slots: list[tuple[int, str]] = []
    while len(reviewer_slots) < len(rows):
        reviewer_slots.extend((index + 1, name) for index, name in enumerate(reviewers))
    reviewer_slots = reviewer_slots[: len(rows)]
    rng.shuffle(reviewer_slots)

    assigned = []
    for review_index, (row, (reviewer_number, reviewer_name)) in enumerate(
        zip(rows, reviewer_slots),
        start=1,
    ):
        output = dict(row)
        output["manual_review_id"] = f"MR{review_index:04d}"
        output["review_bucket"] = review_bucket(row)
        output["assigned_reviewer_number"] = str(reviewer_number)
        output["assigned_reviewer"] = reviewer_name
        output["human_label"] = ""
        output["human_confidence"] = ""
        output["audit_agrees"] = ""
        output["human_review_notes"] = ""
        output["reviewed_at"] = ""
        output["label"] = ""
        output["label_status"] = "manual_review_pending"
        output["label_source"] = ""
        assigned.append(output)
    return assigned


def weak_training_pool(
    rows: list[dict[str, str]],
    held_out_ids: set[str],
    min_confidence: float,
) -> list[dict[str, str]]:
    training_rows = []
    for row in rows:
        if row.get("reddit_id", "") in held_out_ids:
            continue

        confidence = float(row.get("auto_label_confidence") or 0)
        if (
            row.get("auto_label") in TRAINING_LABELS
            and row.get("needs_human_review") == "no"
            and confidence >= min_confidence
        ):
            output = dict(row)
            output["label"] = output["auto_label"]
            output["label_status"] = "weak_labeled_training"
            output["label_source"] = "weak_supervision"
            training_rows.append(output)
    return training_rows


def count_by(rows: list[dict[str, str]], column: str) -> dict[str, int]:
    counts: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.get(column) or "<blank>"] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def ensure_fields(fieldnames: list[str], extra_fields: list[str]) -> list[str]:
    output = list(fieldnames)
    for field in extra_fields:
        if field not in output:
            output.append(field)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create manual-review and weak-training files from weak labels."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Weak-labeled CSV. Defaults to newest file in data/weak_labels.",
    )
    parser.add_argument("--review-size", type=int, default=300)
    parser.add_argument("--min-confidence", type=float, default=0.75)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reviewers", nargs="+", default=DEFAULT_REVIEWERS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.reviewers) < 1:
        raise ValueError("At least one reviewer is required")

    if args.input:
        input_path = args.input
    else:
        try:
            input_path = newest_csv(Path("data/weak_labels"), "diy_repair_weak_labeled_*.csv")
        except FileNotFoundError:
            input_path = newest_csv(Path("data/weak_labels"), "home_repair_weak_labeled_*.csv")
    rows, fieldnames = read_rows(input_path)
    if args.review_size >= len(rows):
        raise ValueError("review-size must be smaller than the full dataset")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    review_path = Path("data/manual_review") / f"manual_review_set_{timestamp}.csv"
    training_path = Path("data/training") / f"weak_training_pool_{timestamp}.csv"
    summary_path = Path("data/splits") / f"weak_manual_split_summary_{timestamp}.json"

    review_rows = assign_reviewers(
        rows=stratified_review_sample(rows, args.review_size, args.seed),
        reviewers=args.reviewers,
        seed=args.seed,
    )
    held_out_ids = {row.get("reddit_id", "") for row in review_rows}
    training_rows = weak_training_pool(
        rows=rows,
        held_out_ids=held_out_ids,
        min_confidence=args.min_confidence,
    )

    extra_review_fields = [
        "manual_review_id",
        "review_bucket",
        "assigned_reviewer_number",
        "assigned_reviewer",
        "human_confidence",
        "reviewed_at",
    ]
    review_fields = ensure_fields(fieldnames, extra_review_fields)
    training_fields = ensure_fields(fieldnames, [])

    write_rows(review_rows, review_fields, review_path)
    write_rows(training_rows, training_fields, training_path)

    per_reviewer_paths = {}
    for reviewer_number, reviewer in enumerate(args.reviewers, start=1):
        reviewer_rows = [
            row
            for row in review_rows
            if row.get("assigned_reviewer_number") == str(reviewer_number)
        ]
        reviewer_path = (
            Path("data/manual_review")
            / f"manual_review_reviewer_{reviewer_number}_{reviewer}_{timestamp}.csv"
        )
        write_rows(reviewer_rows, review_fields, reviewer_path)
        per_reviewer_paths[f"{reviewer_number}-{reviewer}"] = str(reviewer_path)

    summary = {
        "input": str(input_path),
        "manual_review_file": str(review_path),
        "weak_training_file": str(training_path),
        "review_size": len(review_rows),
        "weak_training_size": len(training_rows),
        "min_confidence": args.min_confidence,
        "seed": args.seed,
        "reviewers": {
            str(index + 1): reviewer for index, reviewer in enumerate(args.reviewers)
        },
        "per_reviewer_files": per_reviewer_paths,
        "review_bucket_distribution": count_by(review_rows, "review_bucket"),
        "reviewer_distribution": count_by(review_rows, "assigned_reviewer"),
        "training_label_distribution": count_by(training_rows, "label"),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Manual review rows: {len(review_rows)}")
    print(f"Weak training rows: {len(training_rows)}")
    print(f"Manual review file: {review_path}")
    print(f"Weak training file: {training_path}")
    print(f"Split summary: {summary_path}")
    print("Reviewer distribution:")
    print(json.dumps(summary["reviewer_distribution"], indent=2))
    print("Review bucket distribution:")
    print(json.dumps(summary["review_bucket_distribution"], indent=2))
    print("Training label distribution:")
    print(json.dumps(summary["training_label_distribution"], indent=2))


if __name__ == "__main__":
    main()
