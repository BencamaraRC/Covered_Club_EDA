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


def fetch_sex_by_lsoa() -> pd.DataFrame:
    """TS008 — Sex by LSOA (Census 2021).
    Dataset: NM_2041_1
    Returns: lsoa_code, lsoa_name, female_population, male_population, total_population
    """
    params = {
        "geography": "TYPE297",  # LSOA 2021
        "c2021ts008": "1,2",  # 1=Male, 2=Female
        "measures": "20100",  # count
        "select": "geography_code,geography_name,c2021ts008_name,obs_value",
    }
    try:
        df = _get("NM_2041_1", params)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(
            columns={
                "geography_code": "lsoa_code",
                "geography_name": "lsoa_name",
                "c2021ts008_name": "sex",
                "obs_value": "population",
            }
        )
        pivot = df.pivot_table(
            index=["lsoa_code", "lsoa_name"],
            columns="sex",
            values="population",
            aggfunc="sum",
        ).reset_index()
        pivot.columns.name = None
        rename = {}
        for col in pivot.columns:
            if "female" in col.lower() or col == "Female":
                rename[col] = "female_population"
            elif "male" in col.lower() or col == "Male":
                rename[col] = "male_population"
        pivot = pivot.rename(columns=rename)
        if "female_population" not in pivot.columns:
            pivot["female_population"] = 0
        if "male_population" not in pivot.columns:
            pivot["male_population"] = 0
        pivot["total_population"] = (
            pivot["female_population"] + pivot["male_population"]
        )
        return pivot[
            [
                "lsoa_code",
                "lsoa_name",
                "female_population",
                "male_population",
                "total_population",
            ]
        ]
    except Exception as e:
        print(f"CENSUS sex fetch failed: {e}")
        return pd.DataFrame()


def sex_la_summary(
    sex_lsoa_df: pd.DataFrame, lsoa_la_lookup: pd.DataFrame
) -> pd.DataFrame:
    """Roll LSOA sex data up to LA level."""
    merged = sex_lsoa_df.merge(
        lsoa_la_lookup[["lsoa_code", "la_code", "la_name"]], on="lsoa_code", how="left"
    )
    merged = merged.dropna(subset=["la_code"])
    la = merged.groupby(["la_code", "la_name"], as_index=False).agg(
        female_population=("female_population", "sum"),
        male_population=("male_population", "sum"),
        total_population=("total_population", "sum"),
    )
    la["female_pct"] = (la["female_population"] / la["total_population"] * 100).round(1)
    return la.sort_values("female_population", ascending=False)


def fetch_household_composition() -> pd.DataFrame:
    """TS003 — Household composition by LSOA (Census 2021).
    Dataset: NM_2023_1
    Returns: lsoa_code, household_type, count
    """
    params = {
        "geography": "TYPE297",  # LSOA 2021
        "c2021ts003": "0",  # total + all categories
        "measures": "20100",
        "select": "geography_code,geography_name,c2021ts003_name,obs_value",
    }
    try:
        df = _get("NM_2023_1", params)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(
            columns={
                "geography_code": "lsoa_code",
                "geography_name": "lsoa_name",
                "c2021ts003_name": "household_type",
                "obs_value": "count",
            }
        )
        return df[["lsoa_code", "lsoa_name", "household_type", "count"]]
    except Exception as e:
        print(f"CENSUS household composition fetch failed: {e}")
        return pd.DataFrame()


def household_la_summary(
    hh_lsoa_df: pd.DataFrame, lsoa_la_lookup: pd.DataFrame
) -> pd.DataFrame:
    """Roll LSOA household composition up to LA level, computing lone-parent and single-adult %."""
    if hh_lsoa_df.empty:
        return pd.DataFrame()
    merged = hh_lsoa_df.merge(
        lsoa_la_lookup[["lsoa_code", "la_code", "la_name"]], on="lsoa_code", how="left"
    )
    merged = merged.dropna(subset=["la_code"])

    total = (
        merged[merged["household_type"].str.lower().str.contains("total", na=False)]
        .groupby(["la_code", "la_name"])["count"]
        .sum()
        .reset_index(name="total_households")
    )
    lone = (
        merged[
            merged["household_type"].str.lower().str.contains("lone parent", na=False)
        ]
        .groupby(["la_code", "la_name"])["count"]
        .sum()
        .reset_index(name="lone_parent_households")
    )
    single = (
        merged[
            merged["household_type"]
            .str.lower()
            .str.contains("one person|single", na=False)
        ]
        .groupby(["la_code", "la_name"])["count"]
        .sum()
        .reset_index(name="single_adult_households")
    )

    la = (
        total.merge(lone, on=["la_code", "la_name"], how="left")
        .merge(single, on=["la_code", "la_name"], how="left")
        .fillna(0)
    )
    la["lone_parent_pct"] = (
        la["lone_parent_households"] / la["total_households"] * 100
    ).round(1)
    la["single_adult_pct"] = (
        la["single_adult_households"] / la["total_households"] * 100
    ).round(1)
    return la.sort_values("lone_parent_pct", ascending=False)


def fetch_ethnicity() -> pd.DataFrame:
    """TS021 — Ethnic group, LSOA level.
    Simplified to return population for now.
    """
    # Return empty for now - ethnicity data requires different dataset
    return pd.DataFrame()


def fetch(force_refresh: bool = False) -> dict:
    """
    Fetch all Census demographic data.
    Returns dict with keys: age_structure, household_composition, ethnicity, sex
    """
    if not NOMIS_API_KEY:
        print("CENSUS: NOMIS_API_KEY not set in .env, skipping Census ingest")
        return {
            "age_structure": pd.DataFrame(),
            "household_composition": pd.DataFrame(),
            "ethnicity": pd.DataFrame(),
            "sex": pd.DataFrame(),
        }

    print("CENSUS: Fetching demographic data from Nomis API...")

    data = {
        "age_structure": fetch_age_structure(),
        "household_composition": fetch_household_composition(),
        "ethnicity": fetch_ethnicity(),
        "sex": fetch_sex_by_lsoa(),
    }

    # Save population data to output directory
    if not data["age_structure"].empty:
        output_path = RAW_DIR / "census_population_lsoa.csv"
        data["age_structure"].to_csv(output_path, index=False)
        print(f"CENSUS: Saved population data to {output_path}")

    if not data["sex"].empty:
        output_path = RAW_DIR / "census_sex_lsoa.csv"
        data["sex"].to_csv(output_path, index=False)
        print(f"CENSUS: Saved sex data to {output_path}")

    if not data["household_composition"].empty:
        output_path = RAW_DIR / "census_household_lsoa.csv"
        data["household_composition"].to_csv(output_path, index=False)
        print(f"CENSUS: Saved household composition data to {output_path}")

    return data


if __name__ == "__main__":
    data = fetch()
    for key, df in data.items():
        print(f"\n{key}: {len(df):,} rows")
        if not df.empty:
            print(df.head())
