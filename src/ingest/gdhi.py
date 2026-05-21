"""
ONS Regional Gross Disposable Household Income (GDHI) 2023.

Source: https://www.ons.gov.uk/economy/regionalaccounts/grossdisposablehouseholdincome
Released: September 2025

Tries the ONS Beta API first; falls back to hardcoded values from the
published bulletin if the API endpoint isn't available for this dataset.
"""

from __future__ import annotations
import requests
import pandas as pd

from config import ONS_API_BASE

API_DATASET = "regional-gross-disposable-household-income"


def fetch_via_api() -> pd.DataFrame | None:
    """
    Try ONS Beta API. Returns None if not available.

    Note: at time of writing, ONS Beta API doesn't fully expose GDHI.
    Keep this function as a stub so when ONS publishes the endpoint, you
    just implement the response parsing.
    """
    url = f"{ONS_API_BASE}/datasets/{API_DATASET}/editions"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return None
        # TODO: parse the JSON response into a DataFrame when ONS exposes the
        # dataset. The current schema is documented at
        # https://developer.ons.gov.uk/
        return None
    except requests.RequestException:
        return None


def fetch_from_bulletin() -> pd.DataFrame:
    """Hardcoded fallback from the September 2025 ONS bulletin."""
    return pd.DataFrame(
        [
            {"region": "London", "gdhi_per_head_gbp": 35361},
            {"region": "South East", "gdhi_per_head_gbp": 28500},
            {"region": "East of England", "gdhi_per_head_gbp": 26800},
            {"region": "South West", "gdhi_per_head_gbp": 25900},
            {"region": "UK", "gdhi_per_head_gbp": 24836},
            {"region": "East Midlands", "gdhi_per_head_gbp": 22300},
            {"region": "West Midlands", "gdhi_per_head_gbp": 22000},
            {"region": "Yorkshire/Humber", "gdhi_per_head_gbp": 21800},
            {"region": "North West", "gdhi_per_head_gbp": 21500},
            {"region": "Wales", "gdhi_per_head_gbp": 20900},
            {"region": "Northern Ireland", "gdhi_per_head_gbp": 20100},
            {"region": "North East", "gdhi_per_head_gbp": 19977},
        ]
    )


def fetch(force_refresh: bool = False) -> pd.DataFrame:
    df = fetch_via_api()
    if df is None:
        print("ONS Beta API not available for GDHI — using hardcoded bulletin values")
        df = fetch_from_bulletin()
    return df


if __name__ == "__main__":
    print(fetch())
