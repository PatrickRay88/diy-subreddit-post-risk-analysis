# Home-Repair Reddit Risk Labeling Guide

Use the original post title and body only. Do not use comments, scores, author
history, or subreddit reputation when deciding the label.

## Labels

### `low_risk_diy`

Use when the post sounds cosmetic, minor, or routine and does not suggest active
damage or a safety hazard.

Common signals:
- Painting, staining, caulking, trim, small drywall patches
- Loose hardware, small cosmetic cracks, squeaks
- Questions about tools, materials, or finish quality

### `medium_risk_call_pro`

Use when the post may need a licensed trade, inspection, or timely repair, but
does not sound like immediate danger.

Common signals:
- Plumbing leaks that are contained or slow
- HVAC, furnace, water heater, roofing, breaker, outlet, or wiring issues
- Mold, foundation concerns, pests, recurring water intrusion
- Unclear problems where the homeowner may make things worse by guessing

### `urgent_safety_risk`

Use when the post suggests immediate danger, major active damage, or a condition
where delaying could cause injury or serious property loss.

Common signals:
- Gas smell, carbon monoxide alarm, smoke, burning smell, sparks
- Active flooding, sewage backup, ceiling collapse, fire hazard
- Structural movement, large cracks, sagging, load-bearing concerns
- Exposed live wires, repeated breaker trips with heat/smell/sparking

## Suggested Workflow

1. Keep the original scrape in `data/raw` as the audit copy.
2. Run `python prepare_labeling_dataset.py` to create a working file in `data/labeling`.
3. Label each post manually in the `label` column.
4. Set `label_status` to `labeled`, `needs_second_review`, or `excluded`.
5. Use `review_hint` only as a sorting aid, not as the final answer.
6. If a post fits more than one class, choose the highest realistic risk.
7. If there is not enough information, label conservatively as `medium_risk_call_pro`.
8. Use `label_notes` for difficult calls, short rationale, or exclusion reasons.

Use `exclude_unclear` only for rows that should not be used for model training,
such as deleted posts, pure image posts, jokes, unrelated posts, or posts where
the title/body does not contain enough context.

## Quality Checks

- Label at least 50 posts twice, a few days apart, and compare your consistency.
- If possible, have another person label 50 to 100 posts and compare agreement.
- Keep the classes reasonably balanced. A useful target is 200 to 300 examples
  per class for a 600 to 900 post dataset.
- Remove duplicates, deleted posts, pure photos with no description, and posts
  where the body depends on comments for context.

## Weak-Supervision Audit

If you use `python auto_label_dataset.py`, do not treat the generated labels as
expert ground truth. Open the CSV in `data/audit` and fill in:

- `human_label`: your manual judgment
- `audit_agrees`: `yes` or `no`
- `human_review_notes`: short explanation for disagreements

Report this audit result separately from model accuracy. Model accuracy from
`train_models.py` is accuracy against weak labels, not proof that the model is
right about real-world safety.
