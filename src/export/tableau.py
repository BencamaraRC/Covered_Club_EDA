"""
Write final CSVs for Tableau, one file per dashboard.

Tableau reads CSVs natively; no special format needed.
"""
from __future__ import annotations
import pandas as pd

from config import OUTPUT_DIR


def write(df: pd.DataFrame, name: str) -> None:
    """Write a DataFrame to data/output/{name}.csv."""
    path = OUTPUT_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  -> wrote {path.name} ({len(df):,} rows)")


def write_all(outputs: dict[str, pd.DataFrame]) -> None:
    """Write a dict of {name: dataframe} to OUTPUT_DIR."""
    print(f"\nWriting outputs to {OUTPUT_DIR}")
    for name, df in outputs.items():
        write(df, name)
