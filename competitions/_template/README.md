# {{Competition Name}}

> **Kaggle URL:** https://www.kaggle.com/competitions/{{slug}}
> **Type:** {{tabular | nlp | cv | time-series | other}}
> **Metric:** {{e.g. RMSE, AUC, F1, ...}}
> **Started:** {{YYYY-MM-DD}}

## Problem

A few sentences describing what you're predicting and why it's interesting / what you're hoping to learn.

## Data

- **Source:** `kaggle competitions download -c {{slug}} -p data/raw/`
- **Size:** {{rows / cols / file size}}
- **Notes:** anything tricky -- leakage, time splits, missing fields, weirdness.

```
data/
├── raw/         # downloaded directly from Kaggle, never edited
├── interim/     # intermediate transforms
└── processed/   # final feature tables fed to models
```

## Approach

Track what you tried and what worked. A short bulleted log is enough.

- [ ] EDA -- distribution checks, missingness, target balance
- [ ] Baseline -- one dumb model end-to-end (e.g. mean/mode predictor or LR)
- [ ] Stronger model -- {{e.g. LightGBM with default params}}
- [ ] Feature engineering pass
- [ ] CV strategy locked in -- describe folds and why
- [ ] Hyperparameter tuning
- [ ] Ensembling / stacking
- [ ] Final submission

## Results

| Date       | CV score | Public LB | Private LB | Notes                        |
| ---------- | -------- | --------- | ---------- | ---------------------------- |
| YYYY-MM-DD |          |           |            | baseline                     |

## Layout

```
notebooks/    # EDA and exploratory work, numbered (01_, 02_, ...)
src/          # reusable Python modules for this competition
configs/      # experiment configs (yaml/json)
data/         # gitignored; populated via `kaggle competitions download`
submissions/  # CSVs ready to upload (small, committed)
```

## Reproducing

```powershell
# from the repo root
uv sync                                       # or: pip install -e .[gbm]
cd competitions/{{slug}}
kaggle competitions download -c {{slug}} -p data/raw/
# unzip data/raw/*.zip into data/raw/
python -m src.train                           # whatever your entrypoint is
```
