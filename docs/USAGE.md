# Repo usage / workflow

How a Kaggle competition flows through this repo, end to end. Read top-to-bottom on your first competition; later, jump to whichever step you're on.

## 0. One-time setup

Install dependencies and configure the Kaggle CLI:

```powershell
# Recommended: uv
winget install --id=astral-sh.uv -e
uv sync --extra gbm                          # base + gradient-boosted trees

# Kaggle API token: https://www.kaggle.com/settings -> "Create New Token"
mkdir $env:USERPROFILE\.kaggle
move ~\Downloads\kaggle.json $env:USERPROFILE\.kaggle\
```

You only do this once per machine.

## 1. Pick a competition

Browse https://www.kaggle.com/competitions. Note the **slug** -- the part of the URL after `/competitions/`. Examples:

| URL                                                                  | Slug                                       |
| -------------------------------------------------------------------- | ------------------------------------------ |
| `kaggle.com/competitions/titanic`                                    | `titanic`                                  |
| `kaggle.com/competitions/house-prices-advanced-regression-techniques`| `house-prices-advanced-regression-techniques` |
| `kaggle.com/competitions/playground-series-s4e1`                     | `playground-series-s4e1`                   |

Use that slug verbatim as the folder name; it's also the argument to `kaggle competitions ...`.

## 2. Scaffold the competition folder

```powershell
.\scripts\new-competition.ps1 -Slug <slug> -Download
```

The scaffolder:

1. Validates the slug (kebab-case, matches Kaggle URL format).
2. Copies `competitions/_template/` to `competitions/<slug>/`.
3. Creates `data/{raw,interim,processed}/` (gitignored, local-only).
4. Fills in placeholder fields in the new README (`{{slug}}`, `{{Competition Name}}`, `{{YYYY-MM-DD}}`).
5. With `-Download`, runs `kaggle competitions download` and unzips the archives into `data/raw/`.

After it runs, fill in the README's "Type", "Metric", and "Problem" sections from the competition page.

## 3. EDA

Drop into `competitions/<slug>/notebooks/` and start exploring. Conventions:

- **Number notebooks** so the order of investigation reads top-to-bottom later: `01_eda.ipynb`, `02_target_distribution.ipynb`, `03_feature_ideas.ipynb`, ...
- Read raw data from `../data/raw/`. After cleaning, save intermediate tables to `../data/interim/`. Final feature matrices go to `../data/processed/`.
- **Strip notebook outputs before committing.** Either run `uv run nbstripout notebooks/*.ipynb` before staging, or install the git filter once: `uv run nbstripout --install` from the repo root.

What to look at:

- Target distribution / class balance
- Missingness pattern (random vs. structured)
- Cardinality of categoricals, range of numerics
- Train/test distribution shift -- adversarial validation if you suspect it
- Time structure if dates are involved
- A few rows -- actually `df.sample(20)` and read them

## 4. Baseline

Before tuning anything fancy, get one dumb model end-to-end:

- **Constant predictor.** Mean / mode / class prior. This is the floor; anything else has to beat it.
- **Linear / logistic regression** with default params. The "is the data even useful?" check.
- **LightGBM with default params** on the raw features. The tabular sanity check.

Log each baseline's CV score in the per-competition README results table. The whole point is to anchor expectations before you start chasing improvements -- a "great" model that beats the constant predictor by 0.1% is not actually great.

## 5. Lock in CV early

Pick a CV strategy that matches the data:

| Data shape                            | CV strategy                          |
| ------------------------------------- | ------------------------------------ |
| i.i.d. tabular, balanced              | KFold (5 or 10 folds)                |
| i.i.d. tabular, imbalanced classification | StratifiedKFold                  |
| Time series                           | TimeSeriesSplit / forward-chaining   |
| Group structure (patient, session, ...) | GroupKFold                         |
| Multi-label                           | MultilabelStratifiedKFold (iterstrat) |

Decide once, write it down in the README, and don't change it without good reason -- otherwise CV scores stop being comparable across iterations.

The two silent killers here:

- **Leakage from preprocessing.** Fit scalers / target encoders / imputers *inside* the fold, never on the full dataset.
- **Train/test distribution drift.** If your CV improves but the public LB doesn't, the folds aren't representative of the test set.

## 6. Iterate

Move reusable training code from notebooks into `src/` so you can re-run end-to-end:

```python
# competitions/<slug>/src/train.py
def main(config_path: str) -> None:
    ...

if __name__ == "__main__":
    main("configs/baseline.yaml")
```

Run with: `python -m src.train`.

A reasonable iteration loop:

1. Hypothesis: "If I add feature X, CV should improve because Y."
2. Implement (in a notebook or a `src/` module).
3. Run the CV protocol you locked in at step 5.
4. Log the result in the README results table -- include *what changed*, not just the number.
5. If it helped, keep it. If not, delete it and write down what you learned.

Track experiments. For a small set of runs, the README results table is enough. For lots of runs, install `[tracking]` (`uv sync --extra tracking`) and use mlflow or wandb.

## 7. Submit

```powershell
kaggle competitions submit -c <slug> -f submissions/sub_001.csv -m "lgb baseline, cv=0.8341"
```

Keep submission filenames sequential and informative: `sub_001_baseline.csv`, `sub_002_lgb_tuned.csv`, `sub_003_blend.csv`.

After submission, fill in the public LB column in the results table. Eventually private LB lands once the competition closes -- record that too.

## 8. Promote code to `shared/`

If you reach for the same helper in a third competition, extract it to `shared/`. Examples of code that **belongs** there:

- I/O helpers that accept a competition slug and return the standard `(train, test, sample_submission)` tuple
- Custom CV splitters that aren't in sklearn
- Kaggle-specific metrics (e.g. mean column-wise log loss, MAP@K)
- Reproducibility / seed helpers
- Plotting templates you keep copy-pasting

Examples that do **not** belong in `shared/`:

- Feature engineering specific to one dataset
- Hyperparameter values
- Anything you've only used once or twice

Once a module is in `shared/`, it's importable from any competition (`from shared.io import ...`) without further setup, because `shared/` is registered as a package in `pyproject.toml`.

## Reference: directory cheatsheet

| Path                                  | Purpose                                                      | Tracked?    |
| ------------------------------------- | ------------------------------------------------------------ | ----------- |
| `competitions/<slug>/README.md`       | Problem, approach log, results table                         | yes         |
| `competitions/<slug>/notebooks/`      | EDA + numbered exploration                                   | yes         |
| `competitions/<slug>/src/`            | Reproducible modules (`python -m src.<x>`)                   | yes         |
| `competitions/<slug>/configs/`        | Experiment configs (yaml/json)                               | yes         |
| `competitions/<slug>/data/`           | Raw / interim / processed datasets                           | **no**      |
| `competitions/<slug>/submissions/`    | CSVs uploaded to Kaggle                                      | yes         |
| `competitions/<slug>/models/`         | Trained model checkpoints                                    | **no**      |
| `shared/`                             | Cross-competition utilities                                  | yes         |
| `scripts/`                            | Repo-level scripts (scaffolder, etc.)                        | yes         |

## Anti-patterns

- **Committing data.** `data/` is gitignored everywhere. Don't `git add -f` your way around it.
- **Editing `_template/` for a specific competition.** That folder is the scaffold; edits there propagate to all future competitions. Edit `competitions/<slug>/` instead.
- **Leaving notebook outputs in commits.** Bloats diffs and the repo history. Strip first.
- **Tweaking the CV strategy mid-iteration.** You'll lose the ability to compare runs. Lock it in at step 5.
- **Premature abstraction.** Three uses → extract. Fewer than three → leave it inline.
- **No baseline.** Skipping straight to a fancy model means you never know what "good" looks like for the dataset. Always anchor with at least the constant predictor.
- **Logging only the number.** A row in the results table that just says `0.8341` is useless three weeks later. Always log *what changed*.
