"""
DESNZ Sub-regional Fuel Poverty 2026 report (2024 data).

Source: https://www.gov.uk/government/statistics/sub-regional-fuel-poverty-report-2026-2024-data
Released: 14 May 2026

What this module does:
1. Downloads the LSOA-level fuel poverty table (Table 4)
2. Returns DataFrame with one row per LSOA
3. Provides la_summary() to roll up to LA level using a postcode/LSOA lookup
"""
from __future__ import annotations
import requests
import pandas as pd
from pathlib import Path

from config import RAW_DIR, URLS
from src.ingest.manifest import log

RAW_FILE = RAW_DIR / "fuel_poverty_2024.xlsx"


def download(force: bool = False) -> Path:
    if RAW_FILE.exists() and not force:
        return RAW_FILE

    url = URLS["fuel_poverty_lsoa"]
    if "GET_ACTUAL_FILENAME" in url:
        raise RuntimeError(
            "Fuel poverty URL placeholder not filled in config.py. "
            "Visit the DESNZ sub-regional fuel poverty page and paste the "
            "Table 4 (LSOA) download URL into config.URLS['fuel_poverty_lsoa']."
        )

    print(f"Downloading fuel poverty data from {url}")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    RAW_FILE.write_bytes(r.content)
    log("fuel_poverty_2024", url, RAW_FILE)
    return RAW_FILE


def fetch(force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns LSOA-level fuel poverty. Target columns:
        lsoa_code, n_households, n_fuel_poor, fuel_poor_pct
    """
    path = download(force=force_refresh)

    # Table 4 is the LSOA tab. The exact sheet name and skiprows depend on
    # the workbook layout — verify on download.
    df = pd.read_excel(path, sheet_name="Table 4", skiprows=2)

    column_map = {
        "LSOA Code": "lsoa_code",
        "Number of households": "n_households",
        "Number of households in fuel poverty": "n_fuel_poor",
        "Proportion of households fuel poor (%)": "fuel_poor_pct",
    }
    df = df.rename(columns=column_map)
    df = df[[c for c in column_map.values() if c in df.columns]]
    df = df.dropna(subset=["lsoa_code"])

    # Sanity check
    assert df["fuel_poor_pct"].between(0, 100).all(), "Fuel poverty % out of range"

    return df


def la_summary(df: pd.DataFrame, lsoa_to_la: pd.DataFrame) -> pd.DataFrame:
    """
    Roll fuel poverty up to LA level.

    lsoa_to_la must have columns: lsoa_code, la_code, la_name.
    Returns: la_code, la_name, total_households, fuel_poor_households, fuel_poor_pct
    """
    merged = df.merge(lsoa_to_la, on="lsoa_code", how="left")
    la = (
        merged.groupby(["la_code", "la_name"], as_index=False)
              .agg(
                  total_households=("n_households", "sum"),
                  fuel_poor_households=("n_fuel_poor", "sum"),
              )
    )
    la["fuel_poor_pct"] = la["fuel_poor_households"] / la["total_households"] * 100
    return la.sort_values("fuel_poor_pct", ascending=False)


if __name__ == "__main__":
    df = fetch()
    print(f"Fuel poverty: {len(df):,} LSOAs loaded")
    print(df.head())
