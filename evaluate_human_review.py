"""Evaluate weak labels and saved ML models against human-reviewed labels."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import joblib
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


LABELS = [
    "low_risk_diy",
    "medium_risk_call_pro",
    "urgent_safety_risk",
]


def newest_file(directory: Path, pattern: str) -> Path:
    files = sorted(
        directory.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} found in {directory}")
    return files[0]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def reviewed_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("human_label") in LABELS and (row.get("text") or "").strip()
    ]


def metrics_block(title: str, y_true: list[str], y_pred: list[str]) -> list[str]:
    return [
        title,
        f"Accuracy: {accuracy_score(y_true, y_pred):.3f}",
        f"Macro-F1: {f1_score(y_true, y_pred, average='macro'):.3f}",
        "Confusion matrix rows/columns:",
        ", ".join(LABELS),
        json.dumps(confusion_matrix(y_true, y_pred, labels=LABELS).tolist()),
        "",
        classification_report(y_true, y_pred, labels=LABELS, zero_division=0),
        "",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate weak labels and a saved model against human labels."
    )
    parser.add_argument(
        "--manual-review",
        type=Path,
        default=None,
        help="Completed manual review CSV. Defaults to newest data/manual_review set.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=None,
        help="Saved joblib model. Defaults to newest model in models/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manual_path = args.manual_review or newest_file(
        Path("data/manual_review"), "manual_review_set_*.csv"
    )
    model_path = args.model or newest_file(Path("models"), "best_model_*.joblib")

    rows = read_rows(manual_path)
    eval_rows = reviewed_rows(rows)
    if not eval_rows:
        raise ValueError(
            "No usable human labels found. Fill human_label with one of the "
            "three training labels before running evaluation."
        )

    y_true = [row["human_label"] for row in eval_rows]
    weak_pred = [row.get("auto_label") or "" for row in eval_rows]
    weak_eval_pairs = [
        (truth, pred)
        for truth, pred in zip(y_true, weak_pred)
        if pred in LABELS
    ]

    model = joblib.load(model_path)
    model_pred = model.predict([row["text"] for row in eval_rows]).tolist()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path("reports") / f"human_review_evaluation_{timestamp}.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "Human-Reviewed Evaluation Report",
        "",
        f"Manual review file: {manual_path}",
        f"Model file: {model_path}",
        f"Rows with usable human labels: {len(eval_rows)}",
        f"Human label distribution: {json.dumps(dict(Counter(y_true)), sort_keys=True)}",
        "",
    ]

    if weak_eval_pairs:
        weak_true = [truth for truth, _ in weak_eval_pairs]
        weak_labels = [pred for _, pred in weak_eval_pairs]
        report_lines.extend(
            metrics_block("Weak Labeler vs Human Labels", weak_true, weak_labels)
        )
    else:
        report_lines.extend(
            [
                "Weak Labeler vs Human Labels",
                "No rows had usable weak labels for comparison.",
                "",
            ]
        )

    report_lines.extend(metrics_block("ML Model vs Human Labels", y_true, model_pred))
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Rows evaluated: {len(eval_rows)}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
