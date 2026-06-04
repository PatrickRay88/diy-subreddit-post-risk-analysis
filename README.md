# Home-Repair Reddit Risk Dataset Scraper

This project collects original Reddit post text for a machine-learning dataset
that classifies home-repair posts into:

- `low_risk_diy`
- `medium_risk_call_pro`
- `urgent_safety_risk`

The scraper stores only the post title/body and metadata useful for auditing.
It does not collect comments, so a model cannot learn from advice given by
Reddit commenters.

## Run

Reddit often blocks unauthenticated scraping. Create a Reddit app at
`https://www.reddit.com/prefs/apps`, choose `script`, and put the credentials in
a local `.env` file:

```powershell
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=DataMining:v1.0 (by /u/your_username)

# Optional account login for authenticated script apps
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
```

Then run:

```powershell
python reddit_scraper.py --max-posts 750
```

Outputs are written to `data/raw/` as both JSONL and CSV.

Useful options:

```powershell
python reddit_scraper.py --max-posts 1000 --pages-per-query 3 --delay 3
python reddit_scraper.py --max-posts 750 --max-posts-per-subreddit 150
python reddit_scraper.py --max-posts 750 --max-posts-per-query 75
python reddit_scraper.py --subreddits HomeImprovement Plumbing askanelectrician
python reddit_scraper.py --queries "gas smell" "sparking outlet" "paint peeling"
```

## Prepare For Labeling

After scraping, create a separate manual-labeling file:

```powershell
python prepare_labeling_dataset.py
```

This writes a CSV to `data/labeling/`. Fill in:

- `label`: `low_risk_diy`, `medium_risk_call_pro`, `urgent_safety_risk`, or `exclude_unclear`
- `label_status`: `labeled`, `needs_second_review`, or `excluded`
- `label_notes`: optional short rationale

## Weak Supervision

If fully manual labeling is too time-consuming, generate weak labels:

```powershell
python auto_label_dataset.py
```

This creates:

- `data/weak_labels/`: all rows with auto-label metadata
- `data/training/`: high-confidence weak-labeled rows for model training
- `data/audit/`: a smaller sample to manually check

The weak labeler adds `auto_label`, `auto_label_confidence`,
`auto_label_reason`, `needs_human_review`, and `label_source`. Treat these as
noisy labels, not expert ground truth.

See `PROJECT_STATUS.md` for the current project framing.

## Manual Review Split

For the larger final workflow, hold out a human-reviewed evaluation set:

```powershell
python create_manual_review_split.py --review-size 300 --reviewers Patrick Sarah Max Manthan
```

This creates:

- `data/manual_review/manual_review_set_*.csv`: shared review file
- `data/manual_review/manual_review_reviewer_*.csv`: one file per reviewer
- `data/training/weak_training_pool_*.csv`: weak-labeled training rows with manual-review rows removed
- `data/splits/weak_manual_split_summary_*.json`: split counts

Each manual-review row includes `assigned_reviewer_number` and
`assigned_reviewer`. Reviewers should fill in `human_label`,
`human_confidence`, `audit_agrees`, `human_review_notes`, and `reviewed_at`.

## Train Models

After weak labeling, train the classical ML baselines:

```powershell
python train_models.py
```

This uses only the post `text` column and the high-confidence weak labels. It
writes a report to `reports/` and saves the best pipeline to `models/`.

After the team completes the manual review file, evaluate against human labels:

```powershell
python evaluate_human_review.py --manual-review data\manual_review\manual_review_set_YOUR_TIMESTAMP.csv
```

See `TEAM_REVIEW_INSTRUCTIONS.md` for reviewer assignments and label-entry
rules.

## Columns

- `reddit_id`: Reddit post ID for deduplication
- `subreddit`: source community
- `created_utc`: post creation time in UTC
- `title`: original post title
- `selftext`: original post body
- `text`: title and body joined for ML features
- `permalink`: Reddit link for audit checks
- `score`, `num_comments`, `url`: metadata
- `source_query`: search phrase that found the post
- `review_hint`: weak keyword hint for manual review
- `label`: blank column for manual labels

See `LABELING_GUIDE.md` for the recommended manual labeling rules.
