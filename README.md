# kaggle

Personal home base for Kaggle competitions and ML practice problems. Each competition lives in its own self-contained directory under `competitions/`; reusable code shared across competitions lives in `shared/`.

> See [docs/USAGE.md](docs/USAGE.md) for the end-to-end workflow walk-through (picking a competition → scaffolding → EDA → baseline → iteration → submission → promoting code to `shared/`).

## Layout

```
.
├── competitions/                 # one folder per Kaggle competition
│   ├── _template/                # starter scaffold; copied via scripts/new-competition.ps1
│   │   ├── README.md
│   │   ├── notebooks/            # EDA + exploration (numbered: 01_, 02_, ...)
│   │   ├── src/                  # competition-specific Python modules
│   │   ├── configs/              # experiment configs (yaml/json)
│   │   └── submissions/          # CSVs ready to upload
│   └── <slug>/                   # e.g. titanic, house-prices-advanced-regression
├── shared/                       # cross-competition utilities (importable as `shared`)
├── scripts/
│   └── new-competition.ps1       # scaffolds a new competition from _template
├── docs/
│   └── USAGE.md                  # end-to-end workflow walk-through
├── CLAUDE.md                     # project context for Claude Code
├── pyproject.toml                # deps + uv-friendly project config
└── .gitignore
```

## Getting started

### 1. Install `uv` (recommended) or use plain `pip`

```powershell
# Option A: uv -- fast, modern, lockfile-based
winget install --id=astral-sh.uv -e
uv sync                                  # creates .venv with all base deps
uv sync --extra gbm                      # add gradient-boosted trees (xgb/lgbm/cat)
uv sync --extra dl --extra tracking      # add deep learning + experiment tracking

# Option B: plain pip
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[gbm]"                  # or .[dl], .[gbm,dl,tracking]
```

The `[build-system]` block in `pyproject.toml` makes `shared/` an installed package, so `from shared.io import ...` works from any notebook or script.

### 2. Configure the Kaggle CLI

```powershell
# 1. Generate an API token at https://www.kaggle.com/settings -> "Create New Token"
# 2. Save the kaggle.json it downloads to:
mkdir $env:USERPROFILE\.kaggle
move $HOME\Downloads\kaggle.json $env:USERPROFILE\.kaggle\
```

### 3. (Optional) Configure cloud storage

If you want to read/write data from Cloudflare R2 instead of (or alongside) local disk -- handy for pulling preprocessed datasets across machines without copying them around:

```powershell
Copy-Item .env.example .env
# fill in R2 credentials in .env (see docs/storage.md for token setup)
```

The `shared.storage` module then gives you `r2_uri(...)`, `storage_options()`, and helpers that drop into pandas / Polars / DuckDB / fsspec. See [docs/storage.md](docs/storage.md) for the full walkthrough.

### 4. Start a new competition

```powershell
.\scripts\new-competition.ps1 -Slug titanic -Download
cd competitions/titanic
jupyter lab notebooks/
```

The scaffolder copies `_template/`, creates the gitignored `data/{raw,interim,processed}/` folders, fills in the README placeholders, and (with `-Download`) pulls and unzips the competition data via the Kaggle CLI.

## Conventions

- **One folder per competition**, named with the Kaggle slug (kebab-case, matches the URL).
- **Notebooks for exploration, modules for reproducibility.** EDA goes in `notebooks/`. Anything you want to run end-to-end -- training pipelines, feature builds -- belongs in `src/` so it can be invoked as `python -m src.<entrypoint>`.
- **Number notebooks** so the order of investigation is readable later: `01_eda.ipynb`, `02_baseline.ipynb`, `03_feature_ideas.ipynb`.
- **Strip notebook outputs before committing.** `nbstripout --install` in the repo root sets up a git filter, or just `nbstripout notebooks/*.ipynb` before staging.
- **Track every submission** in the per-competition README's results table -- date, CV score, public LB, private LB, what changed.
- **Data is local-only.** `data/` is gitignored everywhere; download via `kaggle competitions download` and never commit dataset files.
- **Submissions CSVs are committed** -- they're small and they're the artifact you actually shipped.
- **Promote to `shared/` only on the third copy.** First time: write it inline. Second: copy-paste. Third: extract to `shared/`.

## Adding new dependencies

```powershell
uv add lightgbm                  # adds to base deps
uv add --optional gbm xgboost    # adds to the [gbm] extra
```

Or edit `pyproject.toml` directly and run `uv sync`.
