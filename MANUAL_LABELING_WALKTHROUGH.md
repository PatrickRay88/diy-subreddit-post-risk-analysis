# Manual Labeling Walkthrough

Use this walkthrough when filling in your reviewer CSV in
`data/manual_review/`.

The manual-review files contain both generated columns and blank human-review
columns. The generated columns are there to help us audit the weak labeler.
They are not the final answer.

## 1. Open Your Reviewer File

Use your assigned file:

- Patrick: `data/manual_review/manual_review_reviewer_1_Patrick_20260604_181427.csv`
- Sarah: `data/manual_review/manual_review_reviewer_2_Sarah_20260604_181427.csv`
- Max: `data/manual_review/manual_review_reviewer_3_Max_20260604_181427.csv`
- Manthan: `data/manual_review/manual_review_reviewer_4_Manthan_20260604_181427.csv`

Each file has 100 rows.

## 2. Read The Original Post Text

For each row, read:

- `title`
- `selftext`
- `text`

The `text` column usually combines the title and body, so it is often the
easiest column to read.

Do not use Reddit comments, upvotes, author history, or outside assumptions.
The model will only see the original post text, so our human labels should use
the same evidence.

## 3. Understand The Generated Columns

You will see columns that look like labels, but they are generated context:

- `review_hint`: an older rough hint from the labeling-prep step.
- `review_bucket`: the bucket used to balance the manual sample.
- `auto_label`: the weak labeler's best guess.
- `auto_label_confidence`: how confident the weak labeler was.
- `auto_label_reason`: which rule signals fired.
- `auto_label_scores`: numeric rule scores for each possible class.
- `needs_human_review`: whether the weak labeler thought the row was uncertain.

Do not edit those columns.

Important: `needs_review_unclear` in `review_hint` does not mean the row must be
excluded. It only means the early rough hint could not confidently classify the
post. If the post text is clear, still choose the best human risk label.

Also, `needs_human_review = no` does not mean you can skip the row. It only
means the weak labeler thought it had enough signal. Every row in your reviewer
file still needs a human label.

## 4. Choose One Human Label

Fill in `human_label` with exactly one of these:

- `low_risk_diy`
- `medium_risk_call_pro`
- `urgent_safety_risk`
- `exclude_unclear`

Use `low_risk_diy` for cosmetic, minor, routine, or low-stakes maintenance.

Examples:

- Painting, caulk, grout, trim, cabinet hinges
- Small drywall patches
- Wiper blades, air filters, light bulbs, cosmetic car trim
- Basic tool or material questions with no safety concern

Use `medium_risk_call_pro` when a professional, inspection, or careful repair
is probably needed, but the post does not describe an immediate emergency.

Examples:

- Slow or contained leak
- Mold, moisture, roof leak, sewer, septic, HVAC, water heater
- Breaker, outlet, wiring, plumbing concerns without smoke, sparks, heat, or
  burning smell
- Brake replacement, suspension work, drivetrain, transmission, wheel bearing
- Foundation or structural concern without active collapse

Use `urgent_safety_risk` when the post suggests immediate danger or major active
damage.

Examples:

- Gas smell, propane smell, carbon monoxide alarm
- Smoke, sparks, burning smell, hot outlet, melted outlet
- Active flooding, sewage backup, water pouring through ceiling
- Sagging ceiling, bowing wall, collapsing floor
- Brake failure, loose wheel or lug nuts, fuel leak, steering failure

Use `exclude_unclear` only when the row is not usable as a labeled example.

Examples:

- Deleted or empty post
- Photo-only post with no meaningful text
- Joke, rant, update, or unrelated post
- Not enough information to infer risk
- The important context is only in missing photos or comments

If the post is a real DIY repair situation but hard to classify, do not exclude
it. Pick the best risk label and set `human_confidence` to `low`.

## 5. Use The Highest Realistic Risk

If a post contains mixed signals, choose the highest realistic risk supported by
the text.

Examples:

- A caulking post with water leaking into the basement is usually
  `medium_risk_call_pro`.
- A painting post with sparks or burning smell is usually
  `urgent_safety_risk`.
- A car post about routine wiper blades is usually `low_risk_diy`.
- A car post about replacing brakes is usually `medium_risk_call_pro`.
- A car post about brake failure while driving is usually `urgent_safety_risk`.

## 6. Fill Human Confidence

Fill in `human_confidence` with:

- `high`: the label is obvious from the post
- `medium`: the label is reasonable, but there is some ambiguity
- `low`: the post is real, but difficult to judge

Use `low` for hard cases instead of using `exclude_unclear`, as long as the row
contains enough information to make a cautious judgment.

## 7. Compare Against The Auto Label

Fill in `audit_agrees` after you choose `human_label`.

Use `yes` when:

- your `human_label` exactly matches `auto_label`

Use `no` when:

- your `human_label` does not match `auto_label`
- `auto_label` is blank
- you choose `exclude_unclear` and the weak labeler chose a real class

This column is not judging you. It lets us measure where the weak labeler agrees
or disagrees with humans.

## 8. Add A Short Note

Fill in `human_review_notes` with a short explanation. Notes are most useful
when:

- you disagree with `auto_label`
- your confidence is `low`
- you choose `exclude_unclear`
- the post has mixed signals

Good examples:

- `Contained leak, no active flooding described.`
- `Brake failure while driving, urgent safety risk.`
- `Photo-only post; not enough text to classify.`
- `Gas company ruled out gas leak; remaining issue is odor investigation.`

## 9. Add Reviewed Date

Fill in `reviewed_at` with the date you reviewed the row.

Use this format:

```text
2026-06-05
```

## 10. Example Row

Suppose the row says:

```text
Title: Brake Failure. What to do to NEVER experience it again?
Auto label: urgent_safety_risk
Review hint: needs_review_unclear
```

Even though `review_hint` says `needs_review_unclear`, the post is clearly
about brake failure. A good human review would be:

```text
human_label: urgent_safety_risk
human_confidence: high
audit_agrees: yes
human_review_notes: Brake failure is an active vehicle safety issue.
reviewed_at: 2026-06-05
```

## 11. Quick Checklist

For each row:

1. Read `title`, `selftext`, or `text`.
2. Ignore `review_hint` as a final label.
3. Use `auto_label` only as context.
4. Choose one `human_label`.
5. Fill `human_confidence`.
6. Fill `audit_agrees`.
7. Add a short note.
8. Add `reviewed_at`.

