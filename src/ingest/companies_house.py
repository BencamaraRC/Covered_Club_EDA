"""
Companies House — Active gambling & leisure companies by Local Authority.

Source: Companies House bulk data (BasicCompanyDataAsOneFile)
URL: https://download.companieshouse.gov.uk/en_output.html
No API key required. Updated monthly.

SIC codes we filter:
  92000 — Gambling and betting activities
  93110 — Operation of sports facilities
  93290 — Other amusement and recreation activities
  93210 — Activities of amusement parks and theme parks

We join via postcode → LA lookup.
"""
from __future__ import annotations
import io
import requests
import zipfile
import pandas as pd
from pathlib import Path

from config import RAW_DIR

RAW_FILE = RAW_DIR / "companies_house_basic.zip"
EXTRACTED_FILE = RAW_DIR / "companies_house_basic.csv"

CH_URL = "https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-2025-05-01.zip"
CH_URL_FALLBACK = "https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-2025-04-01.zip"

GAMBLING_SICS = {"92000"}
LEISURE_SICS = {"93110", "93290", "93210"}
TARGET_SICS = GAMBLING_SICS | LEISURE_SICS


def download(force: bool = False) -> Path:
    if EXTRACTED_FILE.exists() and not force:
        return EXTRACTED_FILE

    for url in (CH_URL, CH_URL_FALLBACK):
        try:
            print(f"COMPANIES_HOUSE: downloading from {url} (this may take a minute — ~200MB)")
            r = requests.get(url, timeout=300, stream=True, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                RAW_FILE.write_bytes(r.content)
                print(f"COMPANIES_HOUSE: extracting zip...")
                with zipfile.ZipFile(RAW_FILE) as zf:
                    csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
                    with zf.open(csv_name) as src, open(EXTRACTED_FILE, "wb") as dst:
                        dst.write(src.read())
                print(f"COMPANIES_HOUSE: extracted to {EXTRACTED_FILE}")
                return EXTRACTED_FILE
            print(f"COMPANIES_HOUSE: got {r.status_code} from {url}")
        except Exception as e:
            print(f"COMPANIES_HOUSE: download attempt failed ({e})")

    raise RuntimeError(
        "Could not download Companies House data. "
        "Download BasicCompanyDataAsOneFile from "
        "https://download.companieshouse.gov.uk/en_output.html "
        "and extract the CSV to data/raw/companies_house_basic.csv"
    )


def fetch(postcode_la_lookup: pd.DataFrame | None = None, force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns active gambling & leisure company counts by Local Authority.
    Columns: la_code, la_name, gambling_companies, leisure_companies, total_companies

    postcode_la_lookup: DataFrame with columns [postcode, la_code, la_name]
    """
    output_path = RAW_DIR.parent / "output" / "14_leisure_companies_by_la.csv"
    if output_path.exists() and not force_refresh:
        print("COMPANIES_HOUSE: loading from cache")
        return pd.read_csv(output_path)

    try:
        path = download(force=force_refresh)
        # Only read needed columns to keep memory low
        df = pd.read_csv(
            path,
            usecols=lambda c: c in (
                "CompanyName", "CompanyStatus",
                "SICCode.SicText_1", "SICCode.SicText_2",
                "RegAddress.PostCode",
            ),
            dtype=str,
            on_bad_lines="skip",
            low_memory=True,
        )
    except Exception as e:
        print(f"COMPANIES_HOUSE: failed to load CSV ({e}). Returning empty DataFrame.")
        return pd.DataFrame()

    df.columns = [c.strip() for c in df.columns]

    # Filter to active companies only
    if "CompanyStatus" in df.columns:
        df = df[df["CompanyStatus"].str.lower().str.contains("active", na=False)]

    # Extract SIC codes (first 5 chars of SicText fields)
    def extract_sic(val: str | float) -> str:
        if pd.isna(val):
            return ""
        return str(val).strip()[:5]

    df["sic1"] = df.get("SICCode.SicText_1", pd.Series(dtype=str)).apply(extract_sic)
    df["sic2"] = df.get("SICCode.SicText_2", pd.Series(dtype=str)).apply(extract_sic)

    # Keep only target SICs
    mask = df["sic1"].isin(TARGET_SICS) | df["sic2"].isin(TARGET_SICS)
    df = df[mask].copy()
    print(f"COMPANIES_HOUSE: {len(df):,} active gambling/leisure companies found")

    if df.empty:
        return pd.DataFrame()

    df["is_gambling"] = df["sic1"].isin(GAMBLING_SICS) | df["sic2"].isin(GAMBLING_SICS)
    df["postcode_norm"] = df["RegAddress.PostCode"].astype(str).str.strip().str.upper().str.replace(" ", "")

    if postcode_la_lookup is not None and not postcode_la_lookup.empty:
        lookup = postcode_la_lookup.copy()
        lookup["postcode_norm"] = lookup["postcode"].astype(str).str.strip().str.upper().str.replace(" ", "")
        df = df.merge(lookup[["postcode_norm", "la_code", "la_name"]], on="postcode_norm", how="left")
        df = df.dropna(subset=["la_code"])

        la = df.groupby(["la_code", "la_name"]).agg(
            gambling_companies=("is_gambling", "sum"),
            total_companies=("is_gambling", "count"),
        ).reset_index()
        la["leisure_companies"] = la["total_companies"] - la["gambling_companies"]
        la = la.sort_values("total_companies", ascending=False)
        la.to_csv(output_path, index=False)
        print(f"COMPANIES_HOUSE: {len(la):,} LAs → {output_path}")
        return la
    else:
        print("COMPANIES_HOUSE: no LA lookup provided, returning company-level data")
        return df[["CompanyName", "sic1", "postcode_norm", "is_gambling"]]


if __name__ == "__main__":
    df = fetch()
    print(f"\nLeisure companies: {len(df):,} rows")
    print(df.head(10).to_string(index=False))
