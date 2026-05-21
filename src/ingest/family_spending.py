"""
ONS Family Spending in the UK FYE 2024.

Source: https://www.ons.gov.uk/peoplepopulationandcommunity/personalandhouseholdfinances/expenditure/bulletins/familyspendingintheuk/april2023tomarch2024
Released: 10 September 2025

Note: this is NOT LA-level. It's UK + region + income quintile.
We use it for the affordability calculation, applied uniformly to all LAs.

ONS publishes Q1 (£378.60) and Q5 (£948.70) total weekly spend explicitly in
the bulletin. Q2-Q4 must be parsed from the workbook OR interpolated.
"""
from __future__ import annotations
import requests
import pandas as pd
from pathlib import Path

from config import RAW_DIR, URLS
from src.ingest.manifest import log

RAW_FILE = RAW_DIR / "family_spending_2024.xlsx"


def download(force: bool = False) -> Path:
    if RAW_FILE.exists() and not force:
        return RAW_FILE

    url = URLS["family_spending_workbook3"]
    print(f"Downloading Family Spending from {url}")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    RAW_FILE.write_bytes(r.content)
    log("family_spending_2024", url, RAW_FILE)
    return RAW_FILE


def fetch(force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns weekly spend by income quintile. Target columns:
        quintile, total_weekly_gbp, pct_housing_fuel_power, pct_energy_alone, pct_food

    The ONS workbook tab structure changes year to year. The fallback below
    uses interpolated Q2-Q4 values so the pipeline runs end-to-end before
    you've parsed the workbook properly.

    TODO when you have the file open:
        - identify the correct sheet (usually "Table 3.1" or "A6")
        - parse the actual Q2-Q4 weekly spend numbers
        - replace the fallback DataFrame below
    """
    # Attempt to download — useful even if we use the fallback, for auditing
    try:
        download(force=force_refresh)
    except Exception as e:
        print(f"family_spending: download failed ({e}), using bulletin fallback")

    fallback = pd.DataFrame([
        {"quintile": "Q1", "total_weekly_gbp": 378.60, "pct_housing_fuel_power": 27, "pct_energy_alone": 10, "pct_food": 12},
        {"quintile": "Q2", "total_weekly_gbp": 469.00, "pct_housing_fuel_power": 22, "pct_energy_alone": 9,  "pct_food": 12},
        {"quintile": "Q3", "total_weekly_gbp": 589.00, "pct_housing_fuel_power": 19, "pct_energy_alone": 7,  "pct_food": 11},
        {"quintile": "Q4", "total_weekly_gbp": 725.00, "pct_housing_fuel_power": 17, "pct_energy_alone": 6,  "pct_food": 11},
        {"quintile": "Q5", "total_weekly_gbp": 948.70, "pct_housing_fuel_power": 14, "pct_energy_alone": 5,  "pct_food": 10},
    ])
    print("WARNING: family_spending using interpolated Q2-Q4. Parse the workbook for v2.")
    return fallback


if __name__ == "__main__":
    df = fetch()
    print(df)
