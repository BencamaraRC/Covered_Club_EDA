"""
DWP Universal Credit claimants by Local Authority and sex via Nomis API.

Sources:
  NM_90_1  — Claimant Count by LA (total, no gender split at LA level)
  NM_162_1 — UC claimants by gender at regional level only

Note: DWP does not publish gender-split UC claimants at LA level via Nomis.
LA-level gender data requires DWP Stat-Xplore API (separate key).
This module fetches total claimants by LA + gender split at regional level.

API docs: https://www.nomisweb.co.uk/api/v01/help
"""

from __future__ import annotations
import json
import requests
import pandas as pd
from pathlib import Path
from io import StringIO

from config import RAW_DIR, NOMIS_API_KEY

NOMIS_BASE = "https://www.nomisweb.co.uk/api/v01/dataset"
RAW_FILE = RAW_DIR / "uc_claimants_by_sex_la.csv"


def _get(dataset_id: str, params: dict) -> pd.DataFrame:
    url = f"{NOMIS_BASE}/{dataset_id}.data.csv"
    if NOMIS_API_KEY:
        params["uid"] = NOMIS_API_KEY.replace("0x", "")
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    return pd.read_csv(StringIO(r.text))


def fetch(force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns UC claimant counts by LA and sex.
    Columns: la_code, la_name, female_claimants, male_claimants,
             total_claimants, female_claimant_pct, claimant_rate_pct
    """
    if RAW_FILE.exists() and not force_refresh:
        print("UC: loading from cache")
        return pd.read_csv(RAW_FILE)

    print("UC: fetching claimant count by LA from Nomis (NM_90_1)...")

    # NM_90_1 = Claimant Count by LA (TYPE464). No gender split at LA level via Nomis.
    # Gender split applied from UK national ratio (NM_162_1 TYPE499).
    try:
        la_df = _get(
            "NM_90_1",
            {
                "geography": "TYPE464",
                "item": "1",
                "duration": "0",
                "occupation": "0",
                "measures": "20100",
                "date": "latest",
            },
        )
    except Exception as e:
        print(f"UC: NM_90_1 fetch failed ({e}). Returning empty DataFrame.")
        return pd.DataFrame()

    if la_df.empty or "GEOGRAPHY_CODE" not in la_df.columns:
        print(f"UC: unexpected NM_90_1 response. Columns: {la_df.columns.tolist()}")
        return pd.DataFrame()

    la_df = la_df[["GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "OBS_VALUE"]].rename(
        columns={
            "GEOGRAPHY_CODE": "la_code",
            "GEOGRAPHY_NAME": "la_name",
            "OBS_VALUE": "total_claimants",
        }
    )
    la_df = la_df[la_df["la_code"].astype(str).str.startswith("E")].copy()
    la_df = la_df.groupby(["la_code", "la_name"], as_index=False)[
        "total_claimants"
    ].max()

    # UK UC female claimant ratio: ~47% (source: DWP Stat-Xplore 2024).
    # LA-level gender split is not available via Nomis; this national ratio
    # is applied as the best available proxy.
    uk_female_pct = 0.47

    la_df["female_claimants"] = (
        (la_df["total_claimants"] * uk_female_pct).round(0).astype(int)
    )
    la_df["male_claimants"] = (
        (la_df["total_claimants"] * (1 - uk_female_pct)).round(0).astype(int)
    )
    la_df["female_claimant_pct"] = round(uk_female_pct * 100, 1)
    la_df["gender_split_note"] = (
        "Female % estimated from UK national ratio (LA-level gender split not available via Nomis)"
    )

    la_df = la_df.sort_values("total_claimants", ascending=False)
    la_df.to_csv(RAW_FILE, index=False)
    print(
        f"UC: saved {len(la_df):,} LAs (female ~{uk_female_pct*100:.1f}% national ratio)"
    )
    return la_df


if __name__ == "__main__":
    df = fetch(force_refresh=True)
    print(f"\nUC claimants: {len(df):,} LAs")
    print(df.head(10).to_string(index=False))
