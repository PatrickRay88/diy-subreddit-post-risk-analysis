# Project Status And Workflow

## Current Project Summary

This project classifies Reddit DIY repair posts into practical risk levels
using the original post text.

Current research question:

> Can classical machine learning models classify Reddit DIY repair posts into
> low, medium, and urgent risk categories using only the original post text,
> when trained on weakly supervised labels and evaluated with human-reviewed
> examples?

The model is not intended to be a safety tool. It is an exploratory machine
learning class project about text classification, weak supervision, and model
evaluation.

## Current Dataset

The current main dataset contains 2,500 Reddit DIY repair posts, including
home repair, electrical, plumbing, HVAC, general DIY, and automotive/mechanical
repair examples.

Files:

- Raw data: `data/raw/reddit_diy_repair_posts_20260604_180921.csv`
- Labeling copy: `data/labeling/diy_repair_labeling_20260604_180921.csv`
- Full weak-labeled data: `data/weak_labels/diy_repair_weak_labeled_20260604_181413.csv`
- Manual review set: `data/manual_review/manual_review_set_20260604_181427.csv`
- Weak training pool: `data/training/weak_training_pool_20260604_181427.csv`
- Split summary: `data/splits/weak_manual_split_summary_20260604_181427.json`
- Latest model report: `reports/model_report_20260604_181435.txt`
- Project summary doc: `docs/DIY_Repair_Risk_Project_Summary_20260604.docx`

## Labels

The three model classes are:

- `low_risk_diy`
- `medium_risk_call_pro`
- `urgent_safety_risk`

The manual review process also allows:

- `exclude_unclear`

`exclude_unclear` is not a training class. It is used for rows that should not
be evaluated as a real DIY repair risk example.

## What We Built

### 1. Reddit Scraper

`reddit_scraper.py` collects original Reddit post text using Reddit API
credentials stored in a local `.env` file. The `.env` file is ignored by Git.

The scraper saves:

- title
- selftext
- combined text
- subreddit
- permalink
- timestamp
- score and comment count
- source query

Comments are not scraped because the model should not learn from advice given
after the original post.

### 2. Weak Labeler

`auto_label_dataset.py` applies rule-based weak supervision. It searches for
risk signals such as:

- gas smell, carbon monoxide, smoke, sparks
- flooding, sewage backup, collapse
- leaks, mold, plumbing, HVAC, wiring
- vehicle brakes, fuel leaks, loose wheels, steering, suspension, drivetrain
- paint, trim, caulk, drywall patch

The weak labeler writes:

- `auto_label`
- `auto_label_scores`
- `auto_label_confidence`
- `auto_label_reason`
- `needs_human_review`

The weak labeler does not use TF-IDF. It uses hand-written rules and evidence
scores.

### 3. Manual Review Split

`create_manual_review_split.py` created a 400-row held-out manual-review set.

The split is balanced:

- 100 low-risk weak-label rows
- 100 medium-risk weak-label rows
- 100 urgent-risk weak-label rows
- 100 rows flagged as needing human review

Reviewer assignment:

- Patrick: 100 rows
- Sarah: 100 rows
- Max: 100 rows
- Manthan: 100 rows

The manual-review rows are removed from the weak-label training pool.

### 4. Weak Training Pool

After removing the manual-review holdout, the weak-label training pool contains
1,503 high-confidence rows.

Training label distribution:

- `low_risk_diy`: 189
- `medium_risk_call_pro`: 1,058
- `urgent_safety_risk`: 256

### 5. Model Training

`train_models.py` trains classical machine learning models using TF-IDF
features.

The models currently include:

- Logistic Regression
- Naive Bayes
- Linear SVM
- Decision Tree
- Random Forest

Important distinction:

- weak labeler creates rough labels with rules
- TF-IDF creates numeric text features for ML models
- ML models learn from text features and training labels

## Current Model Results

The latest model report is:

`reports/model_report_20260604_181435.txt`

Current best model on a weak-label test split:

- Random Forest
- Accuracy: `0.888`
- Macro-F1: `0.830`

These results are not final human-validated accuracy. They measure agreement
with weak labels. Final evaluation should happen after the manual review file is
completed.

## Why We Need Manual Review

If we only train and test on weak labels, the model may simply learn to imitate
the weak labeler. That would be circular.

The current design avoids that by using:

- weak labels for training
- human-reviewed labels for final evaluation

After the team completes the manual review file, we can compare:

- `auto_label` vs. `human_label`
- model prediction vs. `human_label`

That gives both weak-label quality and model performance against human review.

## Current Task For The Team

Each teammate should review their assigned 100 rows and fill in:

- `human_label`
- `human_confidence`
- `audit_agrees`
- `human_review_notes`
- `reviewed_at`

Main guide:

`LABELING_GUIDE.md`

Quick team instructions:

`TEAM_REVIEW_INSTRUCTIONS.md`

## Next Steps

1. Complete the 300-row manual review.
2. Combine reviewer files if needed, or update the shared manual-review file.
3. Run `evaluate_human_review.py` against the completed manual review file.
4. Report weak-label agreement with humans.
5. Report model performance against human labels.
6. Add error analysis examples to the final writeup.
7. Discuss limitations clearly.

## Suggested Final Claim

This project uses weak supervision to bootstrap a larger training dataset from
Reddit DIY repair posts, then uses a separate human-reviewed set to evaluate
whether classical text models can approximate practical repair-risk categories.
The model is exploratory and should not be treated as a professional safety
decision system.
