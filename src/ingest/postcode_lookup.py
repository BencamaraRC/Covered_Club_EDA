"""
ONS Postcode Directory: postcode -> LSOA -> LA mapping.

Source: https://geoportal.statistics.gov.uk/
Search "ONS Postcode Directory" for the latest release.

The full file is ~1.4GB compressed; the unpacked CSV is several GB. We only
need a few columns. If your machine struggles with the full file, swap in
the National Statistics Postcode Lookup (NSPL) which is the same data
without admin boundary geometries.
"""
from __future__ import annotations
import requests
import pandas as pd
from pathlib import Path

from config import RAW_DIR, URLS
from src.ingest.manifest import log

RAW_FILE = RAW_DIR / "ons_postcode_directory.csv"


def download(force: bool = False) -> Path:
    """
    Download the ONS Postcode Directory. Large file — download once.
    If your connection is slow, manually grab from the geoportal and place
    the file at data/raw/ons_postcode_directory.csv before running.
    """
    if RAW_FILE.exists() and not force:
        return RAW_FILE

    url = URLS["postcode_directory"]
    if "GET_LATEST_VERSION" in url:
        raise RuntimeError(
            "Postcode directory URL placeholder not filled. Visit "
            "https://geoportal.statistics.gov.uk/ and search 'ONS Postcode "
            "Directory' for the latest release URL. Update config.URLS."
        )

    print("Downloading ONS Postcode Directory (large file, ~1.4GB)")
    r = requests.get(url, timeout=600, stream=True)
    r.raise_for_status()
    with open(RAW_FILE, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    log("postcode_directory", url, RAW_FILE)
    return RAW_FILE


def fetch(force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns: postcode, postcode_district, lsoa_code, la_code

    The directory uses cryptic 4-letter column codes; the user guide
    accompanying the download explains each. Common ones:
        pcds   = postcode in standard format ("SW1A 1AA")
        lsoa21 = 2021 LSOA code
        oslaua = current LA code
    """
    path = download(force=force_refresh)

    usecols = ["pcds", "lsoa21", "oslaua"]
    df = pd.read_csv(path, usecols=usecols, dtype=str, low_memory=False)
    df = df.rename(columns={
        "pcds": "postcode",
        "lsoa21": "lsoa_code",
        "oslaua": "la_code",
    })

    # Extract postcode district (outward code, everything before the space)
    df["postcode_district"] = df["postcode"].str.split(" ").str[0]
    df["postcode"] = df["postcode"].str.replace(" ", "").str.upper()

    return df


def district_to_la(df: pd.DataFrame) -> pd.DataFrame:
    """
    Many postcode districts span multiple LAs (e.g. SW9 covers parts of
    Lambeth and Wandsworth). This returns the dominant LA per district
    (the one with the most postcodes).

    Returns: postcode_district, la_code
    """
    counts = (
        df.groupby(["postcode_district", "la_code"])
          .size()
          .reset_index(name="n")
    )
    dominant = (
        counts.sort_values("n", ascending=False)
              .drop_duplicates("postcode_district")
    )
    return dominant[["postcode_district", "la_code"]]


def lsoa_to_la(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build an LSOA -> LA lookup from the postcode directory.
    Each LSOA sits inside exactly one LA, so this is a simple unique pair.

    Returns: lsoa_code, la_code
    """
    return df[["lsoa_code", "la_code"]].drop_duplicates().reset_index(drop=True)


if __name__ == "__main__":
    df = fetch()
    print(f"Postcodes: {len(df):,}")
    print(df.head())
