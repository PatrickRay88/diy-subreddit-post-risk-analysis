# Project Status And Weak-Supervision Plan

## Where We Are

This project started as a supervised text-classification dataset for Reddit
home-repair posts. The goal is to classify the safety or urgency level of an
original post using only the title and body text, not comments.

The current workspace now contains:

- A Reddit scraper that uses official Reddit API credentials from `.env`
- A balanced raw scrape of 750 original posts
- A manual-labeling CSV with blank label fields
- A labeling guide with three core classes

The latest balanced scrape is:

`data/raw/reddit_home_repair_posts_20260529_184424.csv`

The manual-labeling working file is:

`data/labeling/home_repair_labeling_20260529_184535.csv`

## The Labeling Problem

Manually labeling every post is probably more effort than this project needs.
However, fully automated labels can create a different problem: if the labels
come from simple keyword rules and the model is trained on those labels, the
model may only learn to reproduce the same keyword rules.

That would make the project less interesting because the trained model would be
redundant with the label generator.

## Better Approach

The better compromise is weak supervision.

Instead of treating automatic labels as perfect truth, the project uses several
imperfect labeling functions. Each function looks for a type of repair signal,
such as gas risk, electrical danger, active flooding, contained leaks, trade
system issues, mold/foundation concerns, or cosmetic fixes.

The weak labeler then:

- Assigns an `auto_label`
- Gives an `auto_label_confidence`
- Records an `auto_label_reason`
- Fills the training `label` only for high-confidence rows
- Marks uncertain or conflicting rows as `needs_human_review`
- Creates a smaller audit sample for human checking

This means the automatic labels are a noisy teacher, not the final scientific
claim. The machine-learning model can still be evaluated by checking whether it
generalizes beyond the exact trigger phrases used by the weak labeler.

## How This Avoids Being Redundant

The project should not claim that the weak labeler is the final model. Instead,
the project claim should be:

> This project explores whether weakly supervised labels can bootstrap a
> practical training dataset for classifying home-repair risk in Reddit posts,
> and whether classical ML models can generalize from those noisy labels to
> broader language patterns.

The final writeup should include:

- A description of the weak-labeling functions
- The number of rows weak-labeled versus held for review
- A class distribution table
- A small manually checked audit sample
- Model comparisons using TF-IDF plus classical ML models
- A limitation section explaining that weak labels are noisy and not expert
  safety judgments

## Recommended Final Dataset Flow

1. Keep raw scraped data in `data/raw`.
2. Keep manual-labeling files in `data/labeling`.
3. Run weak supervision with `python auto_label_dataset.py`.
4. Train models on `data/training`.
5. Manually review the audit sample in `data/audit`.
6. Report audit accuracy separately from training accuracy.

## Current Generated Outputs

The latest weak-supervision run produced:

- 750 rows with weak-label metadata
- 602 high-confidence weak-labeled training rows
- 120 rows in the human audit sample

Training-label distribution:

- `low_risk_diy`: 153
- `medium_risk_call_pro`: 309
- `urgent_safety_risk`: 140

The latest weak-label files are:

`data/weak_labels/home_repair_weak_labeled_20260529_185646.csv`

`data/training/home_repair_training_weak_20260529_185646.csv`

`data/audit/home_repair_audit_sample_20260529_185646.csv`

The latest model report is:

`reports/model_report_20260529_185652.txt`

The best current model is Logistic Regression with macro-F1 `0.775` on a
weak-label test split. This number should be described as weak-label agreement,
not true expert accuracy.
