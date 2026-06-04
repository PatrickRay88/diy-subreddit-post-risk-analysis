# Team Manual Review Instructions

Use this file as the quick checklist for the team labeling task.

## Files To Use

Shared file:

`data/manual_review/manual_review_set_20260604_172815.csv`

Individual files:

- Patrick: `data/manual_review/manual_review_reviewer_1_Patrick_20260604_172815.csv`
- Sarah: `data/manual_review/manual_review_reviewer_2_Sarah_20260604_172815.csv`
- Max: `data/manual_review/manual_review_reviewer_3_Max_20260604_172815.csv`
- Manthan: `data/manual_review/manual_review_reviewer_4_Manthan_20260604_172815.csv`

Each reviewer has 75 rows.

## Reviewer Numbers

- `1`: Patrick
- `2`: Sarah
- `3`: Max
- `4`: Manthan

You can filter the shared file by either `assigned_reviewer_number` or
`assigned_reviewer`.

## Columns To Fill In

Only fill in these columns:

- `human_label`
- `human_confidence`
- `audit_agrees`
- `human_review_notes`
- `reviewed_at`

Do not edit the generated weak-label columns.

## Valid Values

`human_label`:

- `low_risk_diy`
- `medium_risk_call_pro`
- `urgent_safety_risk`
- `exclude_unclear`

`human_confidence`:

- `low`
- `medium`
- `high`

`audit_agrees`:

- `yes`
- `no`

`reviewed_at`:

- Use a date like `2026-06-04`

## How To Decide The Label

Use only the original post text. Do not use Reddit comments.

Quick rule:

- Cosmetic/minor/routine: `low_risk_diy`
- Needs professional or timely repair: `medium_risk_call_pro`
- Immediate danger or major active damage: `urgent_safety_risk`
- Not enough usable information: `exclude_unclear`

When multiple risks appear, choose the highest realistic risk supported by the
post.

Example:

- A caulking post with a basement leak is probably `medium_risk_call_pro`.
- A painting post with sparks or burning smell is probably `urgent_safety_risk`.
- A small drywall patch with no safety issue is probably `low_risk_diy`.

## How To Use The Auto Label

The `auto_label` is the weak labeler's guess. You may use it as context, but do
not blindly copy it.

Set `audit_agrees = yes` only if your `human_label` matches `auto_label`.

Set `audit_agrees = no` when:

- you disagree with `auto_label`
- `auto_label` is blank
- you choose `exclude_unclear` and the auto label chose a real class

Use `human_review_notes` to briefly explain disagreements.

## Important Project Detail

These 300 manual-review rows are held out from model training. After review,
they will be used to evaluate:

- how often the weak labeler agrees with humans
- how well the trained ML model predicts human labels

That avoids the circular problem of only testing the model against labels
created by the same weak labeler used for training.
