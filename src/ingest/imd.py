"""
MHCLG English Indices of Deprivation 2025.

Source: https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025
Released: 30 October 2025

What this module does:
1. Downloads File 1 (IMD ranks + deciles by LSOA) to data/raw/
2. Returns a tidy DataFrame, one row per LSOA
3. Provides a la_summary() helper that rolls LSOA -> LA
"""
from __future__ import annotations
import requests
import pandas as pd
from pathlib import Path

from config import RAW_DIR, URLS
from src.ingest.manifest import log

RAW_FILE = RAW_DIR / "imd_2025.xlsx"


def download(force: bool = False) -> Path:
    """Download IoD 2025 File 1 to RAW_DIR if not already cached."""
    if RAW_FILE.exists() and not force:
        return RAW_FILE

    url = URLS["imd_2025"]
    if "GET_ACTUAL_FILENAME" in url:
        raise RuntimeError(
            "IoD 2025 URL placeholder not filled in config.py. "
            "Visit https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025 "
            "and paste the direct download URL for File 1 into config.URLS['imd_2025']."
        )

    print(f"Downloading IoD 2025 from {url}")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    RAW_FILE.write_bytes(r.content)
    log("imd_2025", url, RAW_FILE)
    return RAW_FILE


def fetch(force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns a DataFrame with one row per LSOA. Columns (target):
        lsoa_code, lsoa_name, la_code, la_name, imd_rank, imd_decile
    """
    path = download(force=force_refresh)

    # Sheet name varies by release. File 1 is usually the first sheet.
    # Inspect the workbook on download and adjust if needed.
    df = pd.read_excel(path, sheet_name=0)

    # MHCLG column names are long and verbose. Adjust this mapping after
    # you've opened the file once and seen the actual headers.
    column_map = {
        "LSOA code (2021)": "lsoa_code",
        "LSOA name (2021)": "lsoa_name",
        "Local Authority District code (2024)": "la_code",
        "Local Authority District name (2024)": "la_name",
        "Index of Multiple Deprivation (IMD) Rank": "imd_rank",
        "Index of Multiple Deprivation (IMD) Decile": "imd_decile",
    }
    df = df.rename(columns=column_map)
    keep = [c for c in column_map.values() if c in df.columns]
    df = df[keep]

    # Sanity checks
    assert df["lsoa_code"].is_unique, "LSOA codes should be unique"
    assert df["imd_rank"].between(1, 33755).all(), "IMD rank out of range"

    return df


def la_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Roll LSOA-level IMD up to LA-level.

    Returns columns:
        la_code, la_name, n_lsoas, avg_imd_rank, pct_lsoas_top10, la_rank_avg_rank

    la_rank_avg_rank is what MHCLG calls 'Rank of Average Rank' — their
    headline LA-level deprivation measure (1 = most deprived).
    """
    la = (
        df.groupby(["la_code", "la_name"], as_index=False)
          .agg(
              n_lsoas=("lsoa_code", "count"),
              avg_imd_rank=("imd_rank", "mean"),
              pct_lsoas_top10=(
                  "imd_decile",
                  lambda s: (s == 1).sum() / len(s) * 100,
              ),
          )
    )
    la["la_rank_avg_rank"] = la["avg_imd_rank"].rank(method="min").astype(int)
    return la.sort_values("la_rank_avg_rank")


if __name__ == "__main__":
    df = fetch()
    print(f"IMD 2025: {len(df):,} LSOAs loaded")
    print("\nTop 10 LAs by Rank of Average Rank:")
    print(la_summary(df).head(10).to_string(index=False))
