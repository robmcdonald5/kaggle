# Cloud storage (Cloudflare R2)

How to read and write competition data from Cloudflare R2 object storage instead of (or in addition to) the local `data/` directory. R2 speaks the S3 API, costs nothing to read from (zero egress), and the free tier is 10 GB permanent.

## Why R2 over local-only

- **Pull from any machine.** Same script works on your laptop, a VM, or a Kaggle/Colab kernel.
- **Free egress.** Training pipelines re-pull data a lot. Most providers charge $0.09/GB to read it back; R2 charges $0.
- **Same code as local.** With `s3fs` installed, every `pd.read_parquet("path.parquet")` becomes `pd.read_parquet("s3://bucket/path.parquet", storage_options=...)`. No library changes.
- **Versioned snapshots stay reproducible.** Local `data/` is gitignored and per-machine; R2 is shared and durable.

Local `data/` is still the default for raw downloads and per-competition iteration. R2 is for **anything you want to share across machines or pin as a stable reference** -- preprocessed feature tables, large corpora, derived embeddings, model checkpoints.

## One-time setup

### 1. Create an R2 bucket

In the Cloudflare dashboard: **R2 → Create bucket**. Name it whatever you like; `kaggle-data` is the default this repo expects. Location hint can be left as auto.

### 2. Create an API token

**R2 → Manage R2 API Tokens → Create API Token**.

- **Permission:** Object Read & Write
- **Specify bucket:** scope to the bucket you just created (least privilege)
- Save the **Access Key ID** and **Secret Access Key** -- they're shown once.

You'll also need your **Account ID**, the 33-character hex string visible at the top of any R2 page.

### 3. Drop credentials in `.env`

```powershell
Copy-Item .env.example .env
notepad .env   # or your editor of choice
```

Fill in the four R2 fields. `.env` is gitignored; `.env.example` is the only env file committed.

### 4. Sync deps (if you haven't recently)

```powershell
uv sync
```

The base deps now include `s3fs` (S3-compatible filesystem) and `python-dotenv` (auto-loads `.env`). The storage helper picks up your credentials automatically -- no further wiring.

## Usage

All examples assume `from shared.storage import ...`.

### Read a Parquet file with pandas / Polars

```python
import pandas as pd
from shared.storage import r2_uri, storage_options

df = pd.read_parquet(
    r2_uri("titanic/train.parquet"),
    storage_options=storage_options(),
)
```

```python
import polars as pl
from shared.storage import r2_uri, storage_options

df = pl.read_parquet(r2_uri("titanic/train.parquet"), storage_options=storage_options())
```

### Upload a local file

```python
from shared.storage import upload

uri = upload("data/processed/train_features.parquet", "titanic/train_features.parquet")
print(uri)  # s3://kaggle-data/titanic/train_features.parquet
```

### List / check / delete objects

```python
from shared.storage import get_r2_fs, list_keys, exists

list_keys("titanic/")              # ['titanic/train.parquet', 'titanic/test.parquet']
exists("titanic/train.parquet")    # True

fs = get_r2_fs()
fs.rm("kaggle-data/titanic/old.parquet")
```

### Query Parquet in place with DuckDB

DuckDB can query Parquet on R2 without downloading it. Useful for slicing a big table when you only need a column or a filter.

```python
import duckdb
from shared.storage import configure_duckdb, r2_uri

con = duckdb.connect()
configure_duckdb(con)

uri = r2_uri("titanic/train.parquet")
con.sql(f"SELECT survived, count(*) FROM read_parquet('{uri}') GROUP BY survived").show()
```

DuckDB isn't a base dep; install it on demand:

```powershell
uv add duckdb
```

### Reading via fsspec directly

Anything that accepts an `fsspec` filesystem works (pyarrow, dask, etc.):

```python
import pyarrow.parquet as pq
from shared.storage import get_r2_fs

table = pq.read_table("kaggle-data/titanic/train.parquet", filesystem=get_r2_fs())
```

## Suggested key layout

A flat one-prefix-per-competition layout keeps things scannable:

```
kaggle-data/                                 # the bucket
├── titanic/
│   ├── raw/train.csv                        # mirror of competition data, optional
│   ├── processed/train_features.parquet     # outputs from notebook 03_features
│   └── submissions/sub_001.csv              # submission archive (also lives in repo)
├── house-prices/
│   ...
└── shared/
    └── embeddings/<corpus>.parquet          # cross-competition artifacts
```

Use `<slug>/processed/` for derived feature tables you want to pull from another machine without re-running the notebook. Use `shared/` for genuinely cross-competition artifacts (embedding caches, pre-trained model weights you've fine-tuned, etc.).

## Local <-> R2 swap pattern

The whole point of `s3fs` is that the call site barely changes. Keep your code path-agnostic:

```python
# competitions/<slug>/src/io.py
from pathlib import Path
import pandas as pd
from shared.storage import r2_uri, storage_options

LOCAL_DATA = Path(__file__).resolve().parent.parent / "data"

def load_train(source: str = "local") -> pd.DataFrame:
    if source == "local":
        return pd.read_parquet(LOCAL_DATA / "processed" / "train.parquet")
    if source == "r2":
        return pd.read_parquet(
            r2_uri("titanic/processed/train.parquet"),
            storage_options=storage_options(),
        )
    raise ValueError(f"unknown source: {source}")
```

Default to local during iteration; switch to R2 when you want a portable run.

## Troubleshooting

- **`RuntimeError: Environment variable R2_ACCOUNT_ID is not set`** -- `.env` missing or not in the repo root. The helper looks for `.env` next to `pyproject.toml`. Make sure you copied `.env.example` to `.env` and filled it in.
- **`AccessDenied` on read** -- API token is scoped to a different bucket, or `R2_BUCKET` doesn't match the bucket you authorized. Recheck the token's bucket scope in the R2 dashboard.
- **`InvalidArgument: The signature you specified is invalid`** -- usually a wrong region. R2 requires `region_name="auto"`; the helper sets this. If you're calling boto3 directly, set the region to `"auto"`.
- **Slow first call** -- `s3fs` does some metadata setup on first use. Subsequent calls in the same process reuse the connection (the helper caches the filesystem via `lru_cache`).

## When to reach past R2

R2 is great for **files**. It is not great for ad-hoc SQL over many files (use DuckDB locally on Parquet for that), embedding similarity search (use LanceDB or pgvector), or structured JSON queries (use Postgres with JSONB on Neon if you need SQL; otherwise just write `.jsonl` to R2 and read with DuckDB's `read_json_auto`). See [USAGE.md](USAGE.md) for where each piece fits in the broader workflow.
