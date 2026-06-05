# Manual Labeling Walkthrough

This is the single guide for the team manual-review task. Use it when filling
in the reviewer CSV files in `data/manual_review/`.

The manual-review files contain generated weak-label columns and blank
human-review columns. The generated columns are there so we can audit the weak
labeler later. They are not the final answer.

## Goal

Each Reddit post should receive one human judgment about the practical repair
risk described in the original post.

Use only:

- `title`
- `selftext`
- `text`

Do not use:

- Reddit comments
- score or comment count
- author history
- subreddit reputation
- advice given by other users

The model will only see the original post text, so the human labels should use
the same evidence.

## Files To Use

Shared manual-review file:

`data/manual_review/manual_review_set_20260604_181427.csv`

Individual reviewer files:

- Patrick: `data/manual_review/manual_review_reviewer_1_Patrick_20260604_181427.csv`
- Sarah: `data/manual_review/manual_review_reviewer_2_Sarah_20260604_181427.csv`
- Max: `data/manual_review/manual_review_reviewer_3_Max_20260604_181427.csv`
- Manthan: `data/manual_review/manual_review_reviewer_4_Manthan_20260604_181427.csv`

Each reviewer has 100 rows. The full manual-review set has 400 rows.

Reviewer numbers:

- `1`: Patrick
- `2`: Sarah
- `3`: Max
- `4`: Manthan

If using the shared file, filter by `assigned_reviewer_number` or
`assigned_reviewer`.

## Columns To Fill In

Fill in only these columns:

- `human_label`
- `human_confidence`
- `audit_agrees`
- `human_review_notes`
- `reviewed_at`

Do not edit generated columns such as:

- `review_hint`
- `review_bucket`
- `label`
- `label_status`
- `label_source`
- `auto_label`
- `auto_label_confidence`
- `auto_label_reason`
- `auto_label_scores`
- `needs_human_review`
- `manual_review_id`
- `assigned_reviewer_number`
- `assigned_reviewer`

## Generated Columns Explained

Some columns look like labels, but they are only context:

- `review_hint`: an older rough hint from the labeling-prep step.
- `review_bucket`: the bucket used to balance the manual sample.
- `auto_label`: the weak labeler's best guess.
- `auto_label_confidence`: how confident the weak labeler was.
- `auto_label_reason`: which rule signals fired.
- `auto_label_scores`: numeric rule scores for each possible class.
- `needs_human_review`: whether the weak labeler thought the row was uncertain.

Important: `needs_review_unclear` in `review_hint` does not mean the row must be
excluded. It only means an early rough hint could not confidently classify the
post. If the post text is clear, still choose the best human risk label.

Also, `needs_human_review = no` does not mean you can skip the row. It only
means the weak labeler thought it had enough signal. Every row in your reviewer
file still needs a human label.

## Valid Human Labels

Use exactly one value in `human_label`:

- `low_risk_diy`
- `medium_risk_call_pro`
- `urgent_safety_risk`
- `exclude_unclear`

## Label Definitions

### `low_risk_diy`

Use this when the post sounds cosmetic, minor, routine, or low-stakes enough
for a person to research and handle without immediate professional help.

Common signals:

- Painting, staining, peeling paint
- Caulk, grout, trim, baseboards
- Small drywall patches or nail holes
- Loose knobs, cabinet hinges, squeaky doors
- Cosmetic cracks or finish-quality questions
- Basic tool, material, or technique questions with no safety concern
- Wiper blades, air filters, light bulbs, cosmetic car trim

Examples:

- `What caulk should I use around this bathroom counter?`
- `How do I repaint peeling trim?`
- `Can I patch this small drywall hole myself?`
- `How do I replace my windshield wipers?`

### `medium_risk_call_pro`

Use this when the post may need a professional, inspection, or timely repair,
but does not sound like an immediate emergency.

Common signals:

- Slow or contained plumbing leaks
- Water damage, roof leaks, basement water intrusion
- Mold or recurring moisture
- HVAC, furnace, AC, water heater problems
- Breaker, outlet, wiring, plumbing, sewer, or septic concerns without urgent danger signs
- Foundation cracks or structural concerns that are not actively failing
- Brake replacement, suspension, drivetrain, transmission, wheel bearing, or fuel-system questions
- Unclear repair situations where DIY guessing could make the problem worse

Examples:

- `Slow leak under sink has damaged the cabinet floor.`
- `Mold found near basement window after rain.`
- `Breaker keeps tripping, but no smoke or burning smell.`
- `Should I replace my brake pads and rotors myself?`

### `urgent_safety_risk`

Use this when the post suggests possible immediate danger, major active damage,
or a condition where delaying could cause injury or serious property loss.

Common signals:

- Gas smell, propane smell, carbon monoxide alarm
- Smoke, sparks, burning smell, melted outlet, hot outlet
- Active flooding, water pouring or gushing, sewage backup
- Ceiling collapse, sagging ceiling, bowing wall, floor sagging
- Exposed live wires or repeated breaker trips with heat, smoke, smell, or sparks
- Structural movement or load-bearing concerns with visible failure
- Brake failure, loose wheel or lug nuts, fuel leak, steering failure

Examples:

- `Gas smell near furnace.`
- `Outlet sparked and smells burnt.`
- `Water is pouring through the ceiling.`
- `Brake pedal went to the floor while driving.`

### `exclude_unclear`

Use this only when the row should not be used as a human evaluation example.

Common reasons:

- Deleted or removed text
- Pure image post with no meaningful description
- Joke, rant, update, or unrelated post
- Not really a DIY repair or maintenance question
- Too little context to infer risk
- Important information appears to depend on comments or missing photos

Do not use `exclude_unclear` just because the case is hard. If it is a real
DIY repair situation but uncertain, choose the best risk label and set
`human_confidence` to `low`.

## Tie-Breaking Rules

When a post fits more than one class, choose the highest realistic risk that is
supported by the text.

Examples:

- A caulking post with water leaking into the basement is usually
  `medium_risk_call_pro`.
- A painting post with sparks or burning smell is usually
  `urgent_safety_risk`.
- A small cosmetic drywall crack is usually `low_risk_diy` unless the post
  describes structural movement, sagging, or foundation issues.
- Replacing wiper blades is usually `low_risk_diy`.
- Replacing brakes or suspension parts is usually `medium_risk_call_pro` unless
  the post describes active failure.
- A loose wheel, brake failure, fuel leak, or steering failure is usually
  `urgent_safety_risk`.

If the risk is unclear but real, use `medium_risk_call_pro` as the conservative
middle label.

## Human Confidence

Fill in `human_confidence` with one of:

- `high`: the label is clear from the post
- `medium`: the label is reasonable, but there is some ambiguity
- `low`: the post is real but difficult to classify

Use `low` instead of `exclude_unclear` when there is enough information to make
a cautious judgment.

## Audit Agreement

`audit_agrees` compares your human label to the weak labeler's `auto_label`.

Use `yes` when:

- your `human_label` exactly matches `auto_label`

Use `no` when:

- your `human_label` does not match `auto_label`
- `auto_label` is blank
- you choose `exclude_unclear` and the weak labeler chose a real class

This column is not judging the reviewer. It lets us measure where the weak
labeler agrees or disagrees with humans.

## Human Review Notes

Use `human_review_notes` for short explanations, especially when:

- `audit_agrees = no`
- `human_confidence = low`
- you choose `exclude_unclear`
- the post contains mixed risk signals

Good note examples:

- `Leak is contained, no urgent flooding described.`
- `Mentions sparks and burning smell, marking urgent.`
- `Photo-only post; text does not describe the issue.`
- `Gas company ruled out gas leak; remaining issue is odor investigation.`

## Reviewed Date

Fill in `reviewed_at` with the date you reviewed the row.

Use this format:

```text
2026-06-05
```

## Example Row

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

## Why This Matters

The weak labeler created rough labels for a large dataset, but those labels are
not ground truth. The 400 manually reviewed rows are held out from training and
will be used for final evaluation.

Final evaluation will compare:

- weak labeler vs. `human_label`
- trained ML model vs. `human_label`

This is what makes the project more credible than simply training a model to
imitate keyword rules.

## Quick Checklist

For each row:

1. Read `title`, `selftext`, or `text`.
2. Ignore `review_hint` as a final label.
3. Use `auto_label` only as context.
4. Choose one `human_label`.
5. Fill `human_confidence`.
6. Fill `audit_agrees`.
7. Add a short `human_review_notes`.
8. Add `reviewed_at`.

