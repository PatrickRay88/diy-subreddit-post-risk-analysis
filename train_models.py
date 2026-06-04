"""Train classical ML models on the weak-labeled home-repair dataset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier


LABELS = [
    "low_risk_diy",
    "medium_risk_call_pro",
    "urgent_safety_risk",
]


def newest_csv(directory: Path, patterns: list[str]) -> Path:
    files = sorted(
        [
            path
            for pattern in patterns
            for path in directory.glob(pattern)
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        joined = ", ".join(repr(pattern) for pattern in patterns)
        raise FileNotFoundError(f"No files matching {joined} found in {directory}")
    return files[0]


def read_training_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = [
            row
            for row in reader
            if row.get("label") in LABELS and (row.get("text") or "").strip()
        ]
    if not rows:
        raise ValueError(f"No usable training rows found in {path}")
    return rows


def make_models(random_state: int) -> dict[str, Pipeline]:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_features=20000,
    )

    return {
        "logistic_regression": Pipeline(
            [
                ("tfidf", vectorizer),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "naive_bayes": Pipeline(
            [
                ("tfidf", vectorizer),
                ("model", MultinomialNB()),
            ]
        ),
        "linear_svm": Pipeline(
            [
                ("tfidf", vectorizer),
                (
                    "model",
                    LinearSVC(class_weight="balanced", random_state=random_state),
                ),
            ]
        ),
        "decision_tree": Pipeline(
            [
                ("tfidf", vectorizer),
                (
                    "model",
                    DecisionTreeClassifier(
                        max_depth=30,
                        min_samples_leaf=3,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("tfidf", vectorizer),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=250,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def top_terms(pipeline: Pipeline, top_n: int = 12) -> dict[str, list[str]]:
    model = pipeline.named_steps["model"]
    if not hasattr(model, "coef_"):
        return {}

    vectorizer = pipeline.named_steps["tfidf"]
    feature_names = np.array(vectorizer.get_feature_names_out())
    coefficients = model.coef_
    classes = list(model.classes_)
    terms: dict[str, list[str]] = {}

    for index, label in enumerate(classes):
        class_coefficients = coefficients[index]
        top_indices = np.argsort(class_coefficients)[-top_n:][::-1]
        terms[label] = feature_names[top_indices].tolist()
    return terms


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train TF-IDF classical models on weak-labeled Reddit posts."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Training CSV. Defaults to newest file in data/training.",
    )
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input or newest_csv(
        Path("data/training"),
        ["weak_training_pool_*.csv", "home_repair_training_weak_*.csv"],
    )
    rows = read_training_rows(input_path)
    texts = [row["text"] for row in rows]
    labels = [row["label"] for row in rows]

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=args.test_size,
        stratify=labels,
        random_state=args.random_state,
    )

    models = make_models(random_state=args.random_state)
    results = []
    fitted_models: dict[str, Pipeline] = {}

    for name, pipeline in models.items():
        pipeline.fit(x_train, y_train)
        predictions = pipeline.predict(x_test)
        accuracy = accuracy_score(y_test, predictions)
        macro_f1 = f1_score(y_test, predictions, average="macro")
        results.append(
            {
                "model": name,
                "accuracy": accuracy,
                "macro_f1": macro_f1,
                "classification_report": classification_report(
                    y_test, predictions, labels=LABELS, zero_division=0
                ),
                "confusion_matrix": confusion_matrix(
                    y_test, predictions, labels=LABELS
                ).tolist(),
            }
        )
        fitted_models[name] = pipeline

    results.sort(key=lambda item: item["macro_f1"], reverse=True)
    best_name = results[0]["model"]
    best_model = fitted_models[best_name]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path("reports") / f"model_report_{timestamp}.txt"
    model_path = Path("models") / f"best_model_{best_name}_{timestamp}.joblib"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "Home-Repair Risk Classification Model Report",
        "",
        f"Training file: {input_path}",
        f"Rows used: {len(rows)}",
        f"Train rows: {len(x_train)}",
        f"Test rows: {len(x_test)}",
        f"Label distribution: {json.dumps(dict(Counter(labels)), sort_keys=True)}",
        "",
        "Important: these metrics evaluate against weak labels, not expert human ground truth.",
        "Use the audit sample for a separate human sanity check.",
        "",
    ]

    for result in results:
        report_lines.extend(
            [
                f"Model: {result['model']}",
                f"Accuracy: {result['accuracy']:.3f}",
                f"Macro-F1: {result['macro_f1']:.3f}",
                "Confusion matrix rows/columns:",
                ", ".join(LABELS),
                json.dumps(result["confusion_matrix"]),
                "",
                result["classification_report"],
                "",
            ]
        )

    important_terms = top_terms(best_model)
    if important_terms:
        report_lines.append(f"Top weighted terms for best model: {best_name}")
        for label, terms in important_terms.items():
            report_lines.append(f"{label}: {', '.join(terms)}")
        report_lines.append("")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    joblib.dump(best_model, model_path)

    print(f"Best model: {best_name}")
    print(f"Best macro-F1 on weak-label test split: {results[0]['macro_f1']:.3f}")
    print(f"Report: {report_path}")
    print(f"Saved model: {model_path}")


if __name__ == "__main__":
    main()
