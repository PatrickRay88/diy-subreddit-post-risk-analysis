"""Apply weak-supervision labels to the Reddit DIY-repair dataset.

The output is not treated as human ground truth. It is a practical weak-label
dataset with confidence scores, reasons, and a small audit sample for review.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


LOW = "low_risk_diy"
MEDIUM = "medium_risk_call_pro"
URGENT = "urgent_safety_risk"
EXCLUDE = "exclude_unclear"

TRAINING_LABELS = {LOW, MEDIUM, URGENT}


@dataclass(frozen=True)
class RuleGroup:
    name: str
    label: str
    weight: float
    patterns: tuple[str, ...]


RULE_GROUPS = (
    RuleGroup(
        name="gas_or_carbon_monoxide",
        label=URGENT,
        weight=4.0,
        patterns=(
            r"\bgas smell\b",
            r"\bsmell(?:s|ing)? (?:like )?gas\b",
            r"\bnatural gas\b",
            r"\bpropane smell\b",
            r"\bcarbon monoxide\b",
            r"\bco alarm\b",
            r"\bco detector\b",
        ),
    ),
    RuleGroup(
        name="fire_smoke_or_sparks",
        label=URGENT,
        weight=3.5,
        patterns=(
            r"\bspark(?:s|ing|ed)?\b(?!\s+plugs?\b)",
            r"\barc(?:ing|ed)?\b",
            r"\bsmoke\b",
            r"\bburning smell\b",
            r"\bsmell(?:s|ing)? burnt\b",
            r"\bmelted outlet\b",
            r"\bhot outlet\b",
            r"\belectrical fire\b",
            r"\bfire hazard\b",
        ),
    ),
    RuleGroup(
        name="vehicle_brake_wheel_or_steering_danger",
        label=URGENT,
        weight=3.5,
        patterns=(
            r"\bbrake(?:s)? fail(?:ed|ing|ure)?\b",
            r"\bno brakes\b",
            r"\bbrake pedal (?:goes|went) to the floor\b",
            r"\bbrake fluid leak\b",
            r"\bwheel (?:is )?loose\b",
            r"\bwheel (?:came|fell) off\b",
            r"\bloose lug nuts?\b",
            r"\blug nuts? (?:are )?loose\b",
            r"\btire blowout\b",
            r"\bsteering (?:failed|failure|locked|loose)\b",
            r"\bcar (?:fell|slipped) off (?:the )?jack\b",
            r"\bjack stands? failed\b",
        ),
    ),
    RuleGroup(
        name="vehicle_fuel_or_overheat_danger",
        label=URGENT,
        weight=3.2,
        patterns=(
            r"\bfuel leak\b",
            r"\bleaking fuel\b",
            r"\bgasoline leak\b",
            r"\bfuel smell\b",
            r"\bsmell(?:s|ing)? (?:like )?gasoline\b",
            r"\bengine fire\b",
            r"\bcar fire\b",
            r"\bengine overheated\b",
            r"\boverheating while driving\b",
        ),
    ),
    RuleGroup(
        name="active_flooding_or_sewage",
        label=URGENT,
        weight=3.0,
        patterns=(
            r"\bflooding\b",
            r"\bflooded\b",
            r"\bbasement flood(?:ing|ed)?\b",
            r"\bflood(?:ing|ed)? basement\b",
            r"\bwater pouring\b",
            r"\bwater gushing\b",
            r"\bwater rushing\b",
            r"\bsewage backup\b",
            r"\bsewer backup\b",
            r"\btoilet overflow(?:ing)?\b",
            r"\bceiling leak(?:ing)? heavily\b",
        ),
    ),
    RuleGroup(
        name="structural_danger",
        label=URGENT,
        weight=3.0,
        patterns=(
            r"\bceiling collapse(?:d|s|ing)?\b",
            r"\bsagging ceiling\b",
            r"\bbowing wall\b",
            r"\bload[- ]bearing\b",
            r"\bstructural crack\b",
            r"\bstructural damage\b",
            r"\bfloor sag(?:ging)?\b",
        ),
    ),
    RuleGroup(
        name="contained_water_damage",
        label=MEDIUM,
        weight=2.0,
        patterns=(
            r"\bleak(?:s|ing|ed)?\b",
            r"\bwater damage(?:d)?\b",
            r"\bwater intrusion\b",
            r"\bwater coming through\b",
            r"\broof leak\b",
            r"\bbasement leak\b",
            r"\bdrain leak\b",
            r"\bsubfloor\b",
        ),
    ),
    RuleGroup(
        name="trade_system_issue",
        label=MEDIUM,
        weight=2.0,
        patterns=(
            r"\bwater heater\b",
            r"\bfurnace\b",
            r"\bhvac\b",
            r"\bair conditioner\b",
            r"\bac unit\b",
            r"\bbreaker\b",
            r"\boutlets?\b",
            r"\bwiring\b",
            r"\bplumbing\b",
            r"\bsewer smell\b",
            r"\bseptic\b",
        ),
    ),
    RuleGroup(
        name="vehicle_mechanical_system_issue",
        label=MEDIUM,
        weight=2.0,
        patterns=(
            r"\bbrake pads?\b",
            r"\bbrake rotors?\b",
            r"\bbrake replacement\b",
            r"\bbrake service\b",
            r"\bbrake job\b",
            r"\bbrake trouble\b",
            r"\bcalipers?\b",
            r"\bsuspension\b",
            r"\bstruts?\b",
            r"\bshocks?\b",
            r"\bball joints?\b",
            r"\btie rods?\b",
            r"\bcontrol arms?\b",
            r"\bwheel bearings?\b",
            r"\bdrivetrain\b",
            r"\bdrive train\b",
            r"\btransmission\b",
            r"\bclutch\b",
            r"\btiming belt\b",
            r"\bfuel line\b",
            r"\bradiator\b",
            r"\bcoolant leak\b",
            r"\balternator\b",
            r"\bstarter motor\b",
            r"\bcheck engine\b",
            r"\bengine misfire\b",
            r"\bmisfire\b",
            r"\brough idle\b",
            r"\bidle (?:surge|surging|pulsing)\b",
            r"\bengine (?:surge|surging|pulsing)\b",
        ),
    ),
    RuleGroup(
        name="mold_or_foundation_concern",
        label=MEDIUM,
        weight=2.0,
        patterns=(
            r"\bmold\b",
            r"\bblack mold\b",
            r"\bfoundation crack\b",
            r"\bfoundation issue\b",
            r"\bcrawlspace\b",
            r"\btermite\b",
        ),
    ),
    RuleGroup(
        name="cosmetic_or_minor_finish",
        label=LOW,
        weight=2.2,
        patterns=(
            r"\bpaint(?:ing|ed)?\b",
            r"\bpaint peeling\b",
            r"\btrim\b",
            r"\bbaseboard\b",
            r"\bcaulk(?:ing)?\b",
            r"\bgrout\b",
            r"\bdrywall patch\b",
            r"\bnail hole\b",
            r"\bsmall hole\b",
            r"\bcosmetic\b",
            r"\bscratch(?:es|ed)?\b",
            r"\bstain(?:ing|ed)?\b",
            r"\bloose knob\b",
            r"\bcabinet hinge\b",
            r"\bsqueaky door\b",
        ),
    ),
    RuleGroup(
        name="vehicle_low_risk_maintenance",
        label=LOW,
        weight=2.2,
        patterns=(
            r"\boil change\b",
            r"\b(?:replace|replacing|change|changing|install|installing) (?:the )?wiper blades?\b",
            r"\b(?:replace|replacing|change|changing|install|installing) (?:the )?cabin air filter\b",
            r"\b(?:replace|replacing|change|changing|install|installing) (?:the )?air filter\b",
            r"\b(?:replace|replacing|change|changing|install|installing) (?:the )?headlight bulbs?\b",
            r"\b(?:replace|replacing|change|changing|install|installing) (?:the )?taillight bulbs?\b",
            r"\b(?:replace|replacing|change|changing|install|installing) (?:the )?tail light bulbs?\b",
            r"\b(?:replace|replacing|change|changing|install|installing) (?:the )?license plate light\b",
            r"\binterior trim\b",
            r"\bdetailing\b",
            r"\bcar stereo\b",
            r"\b(?:replace|replacing|change|changing|install|installing) (?:the )?spark plugs?\b",
            r"\bspark plug replacement\b",
        ),
    ),
)


def newest_csv(directory: Path, pattern: str) -> Path:
    files = sorted(
        directory.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} found in {directory}")
    return files[0]


def normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def first_match(patterns: tuple[str, ...], text: str) -> str | None:
    for pattern in patterns:
        if re.search(pattern, text):
            return pattern
    return None


def row_text(row: dict[str, str]) -> str:
    text = row.get("text") or ""
    if text:
        return text
    return f"{row.get('title', '')} {row.get('selftext', '')}".strip()


def weak_label(row: dict[str, str], min_confidence: float) -> dict[str, str]:
    text = normalize_text(row_text(row))
    reasons: list[str] = []
    scores: defaultdict[str, float] = defaultdict(float)

    if not text or text in {"[deleted]", "[removed]"}:
        return {
            "auto_label": EXCLUDE,
            "auto_label_confidence": "0.95",
            "auto_label_reason": "missing_or_deleted_text",
            "auto_label_scores": json.dumps({EXCLUDE: 1.0}, sort_keys=True),
            "needs_human_review": "no",
        }

    word_count = len(re.findall(r"\b\w+\b", text))
    if word_count < 10:
        return {
            "auto_label": EXCLUDE,
            "auto_label_confidence": "0.85",
            "auto_label_reason": "too_little_context",
            "auto_label_scores": json.dumps({EXCLUDE: 1.0}, sort_keys=True),
            "needs_human_review": "no",
        }

    for group in RULE_GROUPS:
        match = first_match(group.patterns, text)
        if match:
            scores[group.label] += group.weight
            reasons.append(f"{group.name}:{match}")

    if not scores:
        return {
            "auto_label": "",
            "auto_label_confidence": "0.00",
            "auto_label_reason": "no_labeling_function_matched",
            "auto_label_scores": "{}",
            "needs_human_review": "yes",
        }

    urgent_score = scores.get(URGENT, 0.0)
    medium_score = scores.get(MEDIUM, 0.0)
    low_score = scores.get(LOW, 0.0)

    if urgent_score >= 3.0:
        label = URGENT
    elif medium_score >= 2.0:
        label = MEDIUM
    elif low_score >= 2.0 and medium_score == 0 and urgent_score == 0:
        label = LOW
    elif urgent_score > 0:
        label = URGENT
    elif medium_score > 0:
        label = MEDIUM
    else:
        label = LOW

    top_score = scores[label]
    other_scores = [score for key, score in scores.items() if key != label]
    second_score = max(other_scores) if other_scores else 0.0

    confidence = min(0.95, 0.55 + (top_score * 0.10))
    if top_score - second_score >= 2.0:
        confidence += 0.05
    if second_score > 0:
        confidence -= 0.08
    confidence = max(0.50, min(0.95, confidence))

    needs_review = confidence < min_confidence or second_score >= top_score - 0.5

    return {
        "auto_label": label,
        "auto_label_confidence": f"{confidence:.2f}",
        "auto_label_reason": "; ".join(reasons[:6]),
        "auto_label_scores": json.dumps(dict(scores), sort_keys=True),
        "needs_human_review": "yes" if needs_review else "no",
    }


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


def enrich_rows(
    rows: list[dict[str, str]],
    min_confidence: float,
    fill_labels: bool,
) -> list[dict[str, str]]:
    enriched = []
    for row in rows:
        output = dict(row)
        weak = weak_label(output, min_confidence=min_confidence)
        output.update(weak)

        auto_label = output["auto_label"]
        confidence = float(output["auto_label_confidence"])
        can_fill = (
            fill_labels
            and not output.get("label")
            and auto_label in TRAINING_LABELS
            and confidence >= min_confidence
            and output["needs_human_review"] == "no"
        )

        if can_fill:
            output["label"] = auto_label
            output["label_status"] = "weak_labeled"
            output["label_source"] = "weak_supervision"
        elif output.get("label"):
            output["label_source"] = output.get("label_source") or "human_or_existing"
        else:
            output["label_status"] = "needs_human_review"
            output["label_source"] = ""

        if not output.get("label_notes"):
            output["label_notes"] = ""
        if not output.get("human_label"):
            output["human_label"] = ""
        if not output.get("human_review_notes"):
            output["human_review_notes"] = ""
        if not output.get("audit_agrees"):
            output["audit_agrees"] = ""

        enriched.append(output)
    return enriched


def training_rows(rows: list[dict[str, str]], min_confidence: float) -> list[dict[str, str]]:
    selected = []
    for row in rows:
        confidence = float(row.get("auto_label_confidence") or 0)
        if (
            row.get("label") in TRAINING_LABELS
            and row.get("label_source") == "weak_supervision"
            and confidence >= min_confidence
            and row.get("needs_human_review") == "no"
        ):
            selected.append(row)
    return selected


def audit_rows(rows: list[dict[str, str]], audit_size: int, seed: int) -> list[dict[str, str]]:
    if audit_size <= 0:
        return []

    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, str]]] = {
        LOW: [],
        MEDIUM: [],
        URGENT: [],
        "needs_review": [],
    }

    for row in rows:
        if row.get("needs_human_review") == "yes":
            buckets["needs_review"].append(row)
        elif row.get("auto_label") in TRAINING_LABELS:
            buckets[row["auto_label"]].append(row)

    for bucket_rows in buckets.values():
        rng.shuffle(bucket_rows)

    bucket_names = list(buckets)
    target = max(1, audit_size // len(bucket_names))
    sample: list[dict[str, str]] = []
    selected_ids: set[str] = set()

    for name in bucket_names:
        for row in buckets[name][:target]:
            sample.append(row)
            selected_ids.add(row.get("reddit_id", ""))

    remaining = [row for row in rows if row.get("reddit_id", "") not in selected_ids]
    rng.shuffle(remaining)
    sample.extend(remaining[: max(0, audit_size - len(sample))])
    return sample[:audit_size]


def count_by(rows: list[dict[str, str]], column: str) -> dict[str, int]:
    counts: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.get(column) or "<blank>"] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create weak-supervision labels for the DIY-repair dataset."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Labeling CSV to weak-label. Defaults to newest data/labeling CSV.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.75,
        help="Minimum confidence required to fill the training label.",
    )
    parser.add_argument(
        "--no-fill-labels",
        action="store_true",
        help="Keep label blank and only write auto_label columns.",
    )
    parser.add_argument("--audit-size", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.input:
        input_path = args.input
    else:
        try:
            input_path = newest_csv(Path("data/labeling"), "diy_repair_labeling_*.csv")
        except FileNotFoundError:
            input_path = newest_csv(Path("data/labeling"), "home_repair_labeling_*.csv")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    weak_path = Path("data/weak_labels") / f"diy_repair_weak_labeled_{timestamp}.csv"
    train_path = Path("data/training") / f"diy_repair_training_weak_{timestamp}.csv"
    audit_path = Path("data/audit") / f"diy_repair_audit_sample_{timestamp}.csv"

    rows, fieldnames = read_rows(input_path)
    enriched = enrich_rows(
        rows=rows,
        min_confidence=args.min_confidence,
        fill_labels=not args.no_fill_labels,
    )
    train_rows = training_rows(enriched, min_confidence=args.min_confidence)
    sample_rows = audit_rows(enriched, audit_size=args.audit_size, seed=args.seed)

    extra_fields = [
        "auto_label",
        "auto_label_confidence",
        "auto_label_reason",
        "auto_label_scores",
        "needs_human_review",
        "label_source",
        "human_label",
        "human_review_notes",
        "audit_agrees",
    ]
    all_fields = list(fieldnames)
    for field in ["label_status", "label_notes", *extra_fields]:
        if field not in all_fields:
            all_fields.append(field)

    write_rows(enriched, all_fields, weak_path)
    write_rows(train_rows, all_fields, train_path)
    if sample_rows:
        write_rows(sample_rows, all_fields, audit_path)

    print(f"Input rows: {len(rows)}")
    print(f"Weak-labeled rows written: {len(enriched)}")
    print(f"Training rows written: {len(train_rows)}")
    print(f"Audit rows written: {len(sample_rows)}")
    print(f"Weak labels: {weak_path}")
    print(f"Training set: {train_path}")
    if sample_rows:
        print(f"Audit sample: {audit_path}")
    print("Auto-label distribution:")
    print(json.dumps(count_by(enriched, "auto_label"), indent=2))
    print("Final training-label distribution:")
    print(json.dumps(count_by(train_rows, "label"), indent=2))


if __name__ == "__main__":
    main()
