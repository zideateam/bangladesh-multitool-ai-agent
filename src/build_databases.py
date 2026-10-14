"""Download the three public Bangladesh CSV datasets and create typed SQLite DBs."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download, list_repo_files

DATASETS = {
    "institutions": "Mahadih534/Institutional-Information-of-Bangladesh",
    "hospitals": "Mahadih534/all-bangladeshi-hospitals",
    "restaurants": "Mahadih534/Bangladeshi-Restaurant-Data",
}
ALIASES = {
    "institutions": {"institute_name":"name", "institute_type":"institution_type", "geogrpycal_status":"geographical_status"},
    "hospitals": {"id":"source_id", "name_bangla":"name_bangla", "code":"facility_code", "type":"facility_type", "private":"is_private", "union":"union_name"},
    "restaurants": {"number_of_reviews":"review_count"},
}
INTEGERS = {
    "institutions": {"eiin", "division_id", "district_id", "thana_id", "union_id", "mauza_id"},
    "hospitals": {"source_id", "is_private"},
    "restaurants": {"review_count"},
}
REALS = {"institutions": set(), "hospitals": set(), "restaurants": {"latitude", "longitude", "rating"}}


def normalize(name: str) -> str:
    name = re.sub(r"[^\w]+", "_", name.strip().lower(), flags=re.UNICODE).strip("_")
    return name or "unnamed_column"


def load_csvs(repo: str) -> pd.DataFrame:
    paths = sorted(f for f in list_repo_files(repo_id=repo, repo_type="dataset") if f.lower().endswith(".csv"))
    if not paths:
        raise FileNotFoundError(f"No CSV files found in {repo}. Inspect repository formats.")
    frames = [pd.read_csv(hf_hub_download(repo_id=repo, filename=path, repo_type="dataset"), low_memory=False, dtype=str) for path in paths]
    return pd.concat(frames, ignore_index=True, sort=False)


def prepare(df: pd.DataFrame, table: str) -> tuple[pd.DataFrame, dict[str, str]]:
    aliases = ALIASES[table]
    renamed = [aliases.get(normalize(c), normalize(c)) for c in df.columns]
    if len(renamed) != len(set(renamed)):
        raise ValueError(f"Duplicate column names after normalization for {table}: {renamed}")
    df = df.copy()
    df.columns = renamed
    sqltypes = {}
    for col in df.columns:
        if col in INTEGERS[table]:
            numeric = pd.to_numeric(df[col], errors="coerce")
            if (numeric.dropna() % 1 != 0).any():
                raise ValueError(f"Fractional values in integer column {table}.{col}")
            df[col] = numeric.astype("Int64")
            sqltypes[col] = "INTEGER"
        elif col in REALS[table]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            sqltypes[col] = "REAL"
        else:
            df[col] = df[col].astype("string").str.strip().replace({"": pd.NA})
            sqltypes[col] = "TEXT"
    return df, sqltypes


def build_all(data_dir: str | Path = "data") -> None:
    output = Path(data_dir)
    output.mkdir(parents=True, exist_ok=True)
    for table, repo in DATASETS.items():
        print(f"Fetching {repo}")
        frame, types = prepare(load_csvs(repo), table)
        destination = output / f"{table}.db"
        with sqlite3.connect(destination) as connection:
            frame.to_sql(table, connection, if_exists="replace", index=False, dtype=types)
            for col in ("name", "district", "rating"):
                if col in frame.columns:
                    connection.execute(f'CREATE INDEX IF NOT EXISTS "idx_{table}_{col}" ON "{table}" ("{col}")')
            count = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        print(f"Created {destination}: {count} rows, {len(frame.columns)} columns")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    build_all(parser.parse_args().data_dir)
