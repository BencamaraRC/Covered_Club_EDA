"""
Gambling Commission — Licensed Premises Register.

Source: https://www.gamblingcommission.gov.uk/licensees-and-businesses/licensing/premises-licence
Published as a public CSV (no API key required). Updated monthly.

Licence types we track:
  - Bingo (bingo_halls)
  - Casino (casinos)
  - Betting (betting_shops)
  - Adult Gaming Centre / Family Entertainment Centre (arcades)

We join to LA via postcode → LA lookup (postcode directory already in pipeline).
"""
from __future__ import annotations
import io
import requests
import zipfile
import pandas as pd
from pathlib import Path

from config import RAW_DIR

RAW_FILE = RAW_DIR / "gc_premises_register.csv"

# Gambling Commission premises register — direct CSV download
# If this URL changes, visit: https://www.gamblingcommission.gov.uk/licensees-and-businesses/licensing/premises-licence
GC_PREMISES_URL = (
    "https://www.gamblingcommission.gov.uk/s3fs-public/2025-06/"
    "premises-licence-register.csv"
)

# Fallback: try without date prefix
GC_PREMISES_URL_FALLBACK = (
    "https://www.gamblingcommission.gov.uk/s3fs-public/"
    "premises-licence-register.csv"
)

LICENCE_TYPE_MAP = {
    "bingo": "bingo_halls",
    "casino": "casinos",
    "betting": "betting_shops",
    "adult gaming": "arcades",
    "family entertainment": "arcades",
}


def _classify(licence_type: str) -> str:
    lt = str(licence_type).lower()
    for keyword, category in LICENCE_TYPE_MAP.items():
        if keyword in lt:
            return category
    return "other"


def download(force: bool = False) -> Path:
    if RAW_FILE.exists() and not force:
        return RAW_FILE

    for url in (GC_PREMISES_URL, GC_PREMISES_URL_FALLBACK):
        try:
            print(f"PREMISES: downloading from {url}")
            r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                RAW_FILE.write_bytes(r.content)
                print(f"PREMISES: saved to {RAW_FILE} ({len(r.content):,} bytes)")
                return RAW_FILE
            print(f"PREMISES: got {r.status_code} from {url}")
        except Exception as e:
            print(f"PREMISES: download attempt failed ({e})")

    raise RuntimeError(
        "Could not download premises register. "
        "Download manually from https://www.gamblingcommission.gov.uk/licensees-and-businesses/licensing/premises-licence "
        "and save to data/raw/gc_premises_register.csv"
    )


def fetch(postcode_la_lookup: pd.DataFrame | None = None, force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns venue counts by Local Authority.
    Columns: la_code, la_name, bingo_halls, casinos, betting_shops, arcades,
             other_venues, total_venues, venues_per_10k_pop (if population data available)

    postcode_la_lookup: DataFrame with columns [postcode, la_code, la_name]
      — from src/ingest/postcode_lookup.py. If None, LA join is skipped and
      postcode-level data is returned instead.
    """
    output_path = RAW_DIR.parent / "output" / "13_gambling_venues_by_la.csv"
    if output_path.exists() and not force_refresh:
        print("PREMISES: loading from cache")
        return pd.read_csv(output_path)

    try:
        path = download(force=force_refresh)
        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
    except Exception as e:
        print(f"PREMISES: failed to load CSV ({e}). Returning empty DataFrame.")
        return pd.DataFrame()

    # Normalise column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Find the licence type and postcode columns (column names vary by release)
    licence_col = next((c for c in df.columns if "licence_type" in c or "type" in c), None)
    postcode_col = next((c for c in df.columns if "postcode" in c), None)

    if not licence_col or not postcode_col:
        print(f"PREMISES: unexpected columns: {df.columns.tolist()}")
        return pd.DataFrame()

    df["venue_category"] = df[licence_col].apply(_classify)
    df["postcode_area"] = df[postcode_col].astype(str).str.strip().str.upper()

    if postcode_la_lookup is not None and not postcode_la_lookup.empty:
        # Normalise postcode for join
        lookup = postcode_la_lookup.copy()
        lookup["postcode_norm"] = lookup["postcode"].astype(str).str.strip().str.upper().str.replace(" ", "")
        df["postcode_norm"] = df["postcode_area"].str.replace(" ", "")
        df = df.merge(lookup[["postcode_norm", "la_code", "la_name"]], on="postcode_norm", how="left")
        df = df.dropna(subset=["la_code"])

        pivot = df.groupby(["la_code", "la_name", "venue_category"]).size().reset_index(name="count")
        la_wide = pivot.pivot_table(index=["la_code", "la_name"], columns="venue_category", values="count", fill_value=0).reset_index()
        la_wide.columns.name = None

        for col in ("bingo_halls", "casinos", "betting_shops", "arcades", "other"):
            if col not in la_wide.columns:
                la_wide[col] = 0

        la_wide["total_venues"] = la_wide[["bingo_halls", "casinos", "betting_shops", "arcades", "other"]].sum(axis=1)
        la_wide = la_wide.sort_values("total_venues", ascending=False)
        la_wide.to_csv(output_path, index=False)
        print(f"PREMISES: {len(la_wide):,} LAs with venue data → {output_path}")
        return la_wide
    else:
        # No lookup — return postcode-level counts
        postcode_counts = df.groupby(["postcode_area", "venue_category"]).size().reset_index(name="count")
        print(f"PREMISES: returning {len(postcode_counts):,} postcode-level rows (no LA lookup provided)")
        return postcode_counts


if __name__ == "__main__":
    df = fetch()
    print(f"\nPremises: {len(df):,} rows")
    print(df.head(10).to_string(index=False))
