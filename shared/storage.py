"""Cloudflare R2 storage helpers.

Lets notebooks and scripts read/write competition data from R2 with the same
ergonomics as a local path. Pandas, Polars, PyArrow, fsspec, and DuckDB all
work; under the hood R2 speaks the S3 API, so any S3-aware tool fits.

Quick usage:

    from shared.storage import r2_uri, storage_options, get_r2_fs

    df = pd.read_parquet(r2_uri("titanic/train.parquet"),
                         storage_options=storage_options())

    fs = get_r2_fs()
    fs.put("data/raw/train.csv", "kaggle-data/titanic/train.csv")

    import duckdb
    con = duckdb.connect()
    configure_duckdb(con)
    con.sql("SELECT * FROM read_parquet('s3://kaggle-data/titanic/train.parquet')")

Credentials come from a `.env` at the repo root (auto-loaded). Required vars:
R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY. Optional: R2_BUCKET
(default bucket for r2_uri / upload / download / list_keys / exists).

Credentials are cached after first access. If you rotate them mid-session, call
`get_r2_fs.cache_clear()` and `_credentials.cache_clear()`.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import s3fs
from dotenv import load_dotenv

if TYPE_CHECKING:
    import duckdb


load_dotenv()


def _require(var: str) -> str:
    value = os.environ.get(var)
    if not value:
        raise RuntimeError(
            f"Environment variable {var} is not set. "
            f"Copy .env.example to .env at the repo root and fill in your R2 "
            f"credentials, or export {var} in your shell. See docs/storage.md."
        )
    return value


@lru_cache(maxsize=1)
def _credentials() -> dict[str, Any]:
    return {
        "key": _require("R2_ACCESS_KEY_ID"),
        "secret": _require("R2_SECRET_ACCESS_KEY"),
        "endpoint_url": f"https://{_require('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        "client_kwargs": {"region_name": "auto"},
    }


@lru_cache(maxsize=1)
def get_r2_fs() -> s3fs.S3FileSystem:
    """Cached s3fs.S3FileSystem configured for Cloudflare R2."""
    return s3fs.S3FileSystem(**_credentials())


def storage_options() -> dict[str, Any]:
    """fsspec storage_options dict for pandas / polars / pyarrow."""
    return dict(_credentials())


def r2_uri(key: str, bucket: str | None = None) -> str:
    """Build an `s3://<bucket>/<key>` URI; bucket defaults to $R2_BUCKET."""
    bucket = bucket or _require("R2_BUCKET")
    return f"s3://{bucket.rstrip('/')}/{key.lstrip('/')}"


def configure_duckdb(con: duckdb.DuckDBPyConnection, *, secret_name: str = "kaggle_r2") -> None:
    """Register R2 credentials with a DuckDB connection so `s3://` queries work."""
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    creds = _credentials()
    quote = lambda s: s.replace("'", "''")  # noqa: E731
    endpoint = creds["endpoint_url"].removeprefix("https://")
    con.execute(
        f"""
        CREATE OR REPLACE SECRET {secret_name} (
            TYPE s3,
            KEY_ID '{quote(creds["key"])}',
            SECRET '{quote(creds["secret"])}',
            ENDPOINT '{quote(endpoint)}',
            URL_STYLE 'path',
            REGION 'auto'
        )
        """
    )


def _bucket_key(key: str, bucket: str | None) -> str:
    bucket = bucket or _require("R2_BUCKET")
    return f"{bucket.rstrip('/')}/{key.lstrip('/')}"


def upload(
    local_path: str | os.PathLike[str],
    key: str,
    bucket: str | None = None,
) -> str:
    fs = get_r2_fs()
    target = _bucket_key(key, bucket)
    fs.put(str(local_path), target, recursive=Path(local_path).is_dir())
    return f"s3://{target}"


def download(
    key: str,
    local_path: str | os.PathLike[str],
    bucket: str | None = None,
    *,
    recursive: bool = False,
) -> Path:
    fs = get_r2_fs()
    fs.get(_bucket_key(key, bucket), str(local_path), recursive=recursive)
    return Path(local_path)


def list_keys(prefix: str = "", bucket: str | None = None) -> list[str]:
    """List object keys under a prefix. Materializes the full list; for very
    large prefixes use `get_r2_fs().find(...)` as a generator instead."""
    fs = get_r2_fs()
    bucket = bucket or _require("R2_BUCKET")
    entries: list[str] = fs.ls(_bucket_key(prefix, bucket), detail=False)
    return [e.removeprefix(f"{bucket}/") for e in entries]


def exists(key: str, bucket: str | None = None) -> bool:
    return get_r2_fs().exists(_bucket_key(key, bucket))
