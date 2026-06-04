# Team Manual Review Instructions

Use the manual-review files created from the 2,000-post dataset.

## Reviewers

- `1`: Patrick
- `2`: Sarah
- `3`: Max
- `4`: Manthan

Each person has 75 rows.

## Files

Shared file:

`data/manual_review/manual_review_set_20260604_172815.csv`

Individual files:

- Patrick: `data/manual_review/manual_review_reviewer_1_Patrick_20260604_172815.csv`
- Sarah: `data/manual_review/manual_review_reviewer_2_Sarah_20260604_172815.csv`
- Max: `data/manual_review/manual_review_reviewer_3_Max_20260604_172815.csv`
- Manthan: `data/manual_review/manual_review_reviewer_4_Manthan_20260604_172815.csv`

## What To Fill In

For each row, fill in:

- `human_label`
- `human_confidence`
- `audit_agrees`
- `human_review_notes`
- `reviewed_at`

Valid `human_label` values:

- `low_risk_diy`
- `medium_risk_call_pro`
- `urgent_safety_risk`
- `exclude_unclear`

Valid `human_confidence` values:

- `low`
- `medium`
- `high`

Use `audit_agrees = yes` if your `human_label` matches `auto_label`.
Use `audit_agrees = no` if you disagree with the weak labeler.

Use `human_review_notes` for short explanations, especially when
`audit_agrees = no`.

Use `reviewed_at` as a date, such as `2026-06-04`.

## Important

Do not change `auto_label`, `auto_label_scores`, `auto_label_reason`, or
`auto_label_confidence`. Those columns are the weak labeler's output and are
used later to compare weak labels against human labels.

The manual-review rows are held out from the weak-label training pool, so they
can be used for a less circular final evaluation.
