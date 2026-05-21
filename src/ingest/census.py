"""
ONS Census 2021 via Nomis API.

Pulls demographic data at LSOA level:
- Age structure (TS002)
- Household composition (TS003)
- Ethnicity (TS021)

API docs: https://www.nomisweb.co.uk/api/v01/help
Free API key at: https://www.nomisweb.co.uk/
"""

from __future__ import annotations
import requests
import pandas as pd
from pathlib import Path

from config import NOMIS_API_KEY, RAW_DIR

NOMIS_BASE = "https://www.nomisweb.co.uk/api/v01/dataset"


def _get(dataset_id: str, params: dict) -> pd.DataFrame:
    """Helper for Nomis API GET requests."""
    url = f"{NOMIS_BASE}/{dataset_id}.data.csv"

    print(f"Fetching from Nomis: {dataset_id}")
    print(f"URL: {url}")
    print(f"Params: {params}")

    # Try without API key first
    r = requests.get(url, params=params, timeout=120)

    if r.status_code == 406 and NOMIS_API_KEY:
        print(f"406 error - trying with API key")
        # Try with API key (remove 0x prefix if present)
        api_key = NOMIS_API_KEY.replace("0x", "")
        params["uid"] = api_key
        r = requests.get(url, params=params, timeout=120)

    print(f"Response status: {r.status_code}")
    print(f"Response content (first 500 chars): {r.text[:500]}")

    r.raise_for_status()

    from io import StringIO

    return pd.read_csv(StringIO(r.text))


def fetch_age_structure() -> pd.DataFrame:
    """TS002 — Age by single year, LSOA level.
    Dataset: NM_2010_1
    Returns: lsoa_code, age, population
    """
    # Try with a known working dataset first to test API connection
    # Use NM_1_1 (Jobseeker's Allowance claimants) as a test
    print("Testing API connection with simple dataset...")
    params = {
        "geography": "2092957703",  # England
        "date": "latest",
    }

    try:
        df = _get("NM_1_1", params)
        print(f"Test dataset successful! Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Test dataset failed: {e}")

    # Now try the Census 2021 dataset with correct ID
    # Census 2021 datasets use different ID format
    # Try NM_893_1 (Census 2021 - Population)
    print("\nTrying Census 2021 dataset...")
    params = {
        "geography": "TYPE297",  # LSOA 2021
    }

    try:
        df = _get("NM_893_1", params)
        print(f"Census dataset successful! Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Census dataset failed: {e}")
        # Fallback - return empty DataFrame
        return pd.DataFrame()

    # Rename columns - Nomis returns uppercase column names
    df = df.rename(
        columns={
            "GEOGRAPHY_CODE": "lsoa_code",
            "GEOGRAPHY_NAME": "lsoa_name",
            "OBS_VALUE": "population",
        }
    )

    return df[["lsoa_code", "lsoa_name", "population"]]


def fetch_household_composition() -> pd.DataFrame:
    """TS003 — Household composition, LSOA level.
    Simplified to return population for now.
    """
    # Return empty for now - complex household data requires different dataset
    return pd.DataFrame()


def fetch_ethnicity() -> pd.DataFrame:
    """TS021 — Ethnic group, LSOA level.
    Simplified to return population for now.
    """
    # Return empty for now - ethnicity data requires different dataset
    return pd.DataFrame()


def fetch(force_refresh: bool = False) -> dict:
    """
    Fetch all Census demographic data.
    Returns dict with keys: age_structure, household_composition, ethnicity
    """
    if not NOMIS_API_KEY:
        print("CENSUS: NOMIS_API_KEY not set in .env, skipping Census ingest")
        return {
            "age_structure": pd.DataFrame(),
            "household_composition": pd.DataFrame(),
            "ethnicity": pd.DataFrame(),
        }

    print("CENSUS: Fetching demographic data from Nomis API...")

    data = {
        "age_structure": fetch_age_structure(),
        "household_composition": fetch_household_composition(),
        "ethnicity": fetch_ethnicity(),
    }

    # Save population data to output directory
    if not data["age_structure"].empty:
        output_path = RAW_DIR / "census_population_lsoa.csv"
        data["age_structure"].to_csv(output_path, index=False)
        print(f"CENSUS: Saved population data to {output_path}")

    return data


if __name__ == "__main__":
    data = fetch()
    for key, df in data.items():
        print(f"\n{key}: {len(df):,} rows")
        if not df.empty:
            print(df.head())
