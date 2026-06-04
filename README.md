# DIY Repair Reddit Post Risk Analysis

This project builds a text-classification pipeline for Reddit DIY repair posts.
The goal is to classify original post text into practical repair-risk levels:

- `low_risk_diy`
- `medium_risk_call_pro`
- `urgent_safety_risk`

The final workflow uses weak supervision for scale and human review for a less
circular evaluation.

## Current Status

Current main dataset:

- 2,500 scraped Reddit posts
- 2,500 weak-labeled rows
- 400 held-out manual-review rows
- 1,503 high-confidence weak-labeled training rows after removing the holdout

Current reviewer assignments:

- Patrick: 100 rows
- Sarah: 100 rows
- Max: 100 rows
- Manthan: 100 rows

Start here:

- `PROJECT_STATUS.md`: current project summary
- `LABELING_GUIDE.md`: detailed label rules
- `TEAM_REVIEW_INSTRUCTIONS.md`: short teammate instructions

## Key Files

- Raw data: `data/raw/reddit_diy_repair_posts_20260604_180921.csv`
- Full weak-labeled data: `data/weak_labels/diy_repair_weak_labeled_20260604_181413.csv`
- Manual review set: `data/manual_review/manual_review_set_20260604_181427.csv`
- Weak training pool: `data/training/weak_training_pool_20260604_181427.csv`
- Latest model report: `reports/model_report_20260604_181435.txt`
- Project summary doc: `docs/DIY_Repair_Risk_Project_Summary_20260604.docx`

## Method Overview

The project has two labeling/evaluation layers.

First, `auto_label_dataset.py` creates weak labels using hand-written rules.
These rules look for phrases associated with gas, sparks, flooding, leaks,
mold, wiring, HVAC, plumbing, paint, caulk, trim, vehicle brakes, fuel leaks,
tires, steering, suspension, and similar repair signals.

Second, the team manually reviews a held-out 300-row sample. Those rows are not
used for weak-label training. They will be used for final evaluation.

This avoids the main circularity problem:

- weak labels are used for training
- human labels are used for final evaluation

## Setup

Install dependencies:

```powershell
pip install -r requirements.txt
```

Reddit scraping uses API credentials from `.env`. The `.env` file is ignored by
Git and should not be committed.

Example `.env` format:

```powershell
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=DataMining:v1.0 (by /u/your_username)

# Optional account login for authenticated script apps
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
```

## Recreate The Current Pipeline

Scrape posts:

```powershell
python reddit_scraper.py --max-posts 2500 --max-posts-per-subreddit 350 --max-posts-per-query 125 --pages-per-query 4 --delay 1
```

Prepare a labeling copy:

```powershell
python prepare_labeling_dataset.py --input data\raw\reddit_diy_repair_posts_20260604_180921.csv --output data\labeling\diy_repair_labeling_20260604_180921.csv
```

Weak-label the full dataset:

```powershell
python auto_label_dataset.py --input data\labeling\diy_repair_labeling_20260604_180921.csv --audit-size 0
```

Create the held-out manual-review split:

```powershell
python create_manual_review_split.py --input data\weak_labels\diy_repair_weak_labeled_20260604_181413.csv --review-size 400 --reviewers Patrick Sarah Max Manthan --seed 42
```

Train baseline models on the weak-label training pool:

```powershell
python train_models.py --input data\training\weak_training_pool_20260604_181427.csv
```

After human review is complete, evaluate against human labels:

```powershell
python evaluate_human_review.py --manual-review data\manual_review\manual_review_set_20260604_181427.csv
```

## Manual Review

Reviewers should fill in only:

- `human_label`
- `human_confidence`
- `audit_agrees`
- `human_review_notes`
- `reviewed_at`

Do not edit:

- `auto_label`
- `auto_label_scores`
- `auto_label_confidence`
- `auto_label_reason`
- `needs_human_review`

Valid `human_label` values:

- `low_risk_diy`
- `medium_risk_call_pro`
- `urgent_safety_risk`
- `exclude_unclear`

See `LABELING_GUIDE.md` for the decision rules.

## Model Training

`train_models.py` uses TF-IDF to convert post text into numeric features. It
then trains:

- Logistic Regression
- Naive Bayes
- Linear SVM
- Decision Tree
- Random Forest

The saved model pipeline includes both the TF-IDF vectorizer and the trained
model.

Current best weak-label test result:

- Random Forest
- Accuracy: `0.888`
- Macro-F1: `0.830`

These metrics are weak-label agreement, not final human-validated accuracy.

## Evaluation Plan

After the team completes the manual review:

1. Compare `auto_label` to `human_label`.
2. Compare trained model predictions to `human_label`.
3. Report accuracy, macro-F1, per-class precision/recall/F1, and confusion matrix.
4. Inspect errors, especially urgent posts predicted as medium or low.

The final writeup should clearly state that the classifier is exploratory and
not a professional safety tool.
