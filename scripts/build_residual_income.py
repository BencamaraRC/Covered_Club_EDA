"""
Build per-LA residual income ("money after bills") from real public data and
attach it to the CLPI composite.

Sources (downloaded fresh; cached copies in data/raw/ are reused if present):
  - ONS "Income estimates for small areas, E&W" FYE2023 — net income After
    Housing Costs by MSOA (rolled up to Local Authority).
  - GOV.UK "Council Tax levels set by local authorities in England 2024-25",
    Table 7a — average Band D by authority (ONS code).

Outputs:
  - data/output/16_residual_income_la.csv   (all LAs we can build)
  - data/output/09_clpi_composite.csv        (adds residual + score_residual)

Run:  python -m scripts.build_residual_income      (from project root)

Energy/food/transport are national assumptions in config.BILL_ASSUMPTIONS;
council tax is per-LA. Water is already inside AHC and is not subtracted.
This is the reproducible generator for the committed CSVs the Streamlit app
reads (Streamlit Cloud does not run the full pipeline).
"""
from __future__ import annotations
import re
from pathlib import Path

import pandas as pd
import requests

from config import OUTPUT_DIR, RAW_DIR, BILL_ASSUMPTIONS
from src.analyse.residual_income import compute_residual, score_residual

INCOME_URL = (
    "https://ons.gov.uk/file?uri=/employmentandlabourmarket/peopleinwork/"
    "earningsandworkinghours/datasets/"
    "smallareaincomeestimatesformiddlelayersuperoutputareasenglandandwales/"
    "financialyearending2023/datasetfinal.xlsx"
)
COUNCIL_TAX_URL = (
    "https://assets.publishing.service.gov.uk/media/662a4da155e1582b6ca7e608/"
    "Table_7_24-25__revised_.ods"
)
INCOME_FILE = RAW_DIR / "ons_small_area_income_fye2023.xlsx"
COUNCIL_TAX_FILE = RAW_DIR / "gov_council_tax_2024_25.ods"

# National average Band D (incl. adult social care) 2024-25, for the
# per-dwelling scaling and as the fallback for LAs absent from Table 7a
# (shire districts, whose bill is county+district+precepts).
NAT_AVG_BAND_D = 2171


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _download(url: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def load_ahc_by_la() -> pd.DataFrame:
    """Mean net income After Housing Costs per Local Authority."""
    _download(INCOME_URL, INCOME_FILE)
    df = pd.read_excel(
        INCOME_FILE, sheet_name="Net income after housing costs", header=3
    )
    df.columns = [c.strip() for c in df.columns]
    val = next(
        c for c in df.columns if "after housing costs" in c.lower() and "income" in c.lower()
    )
    df = df.rename(
        columns={
            "Local authority code": "la_code",
            "Local authority name": "la_name",
            val: "ahc_income",
        }
    )
    df["ahc_income"] = pd.to_numeric(df["ahc_income"], errors="coerce")
    return (
        df.groupby(["la_code", "la_name"], as_index=False)["ahc_income"]
        .mean()
        .round(0)
    )


def load_council_tax_by_code() -> pd.DataFrame:
    """Average Band D (incl. ASC, coalescing parish-inclusive/exclusive) by code."""
    _download(COUNCIL_TAX_URL, COUNCIL_TAX_FILE)
    ct = pd.read_excel(COUNCIL_TAX_FILE, engine="odf", sheet_name="Table_7a", header=2)
    ct.columns = [str(c).strip() for c in ct.columns]
    incl = next(
        c for c in ct.columns if "and parish precepts (Band D)" in c and c.startswith("Average")
    )
    excl = next(
        c for c in ct.columns if "excluding parish precepts (Band D)" in c and c.startswith("Average")
    )
    ct = ct.rename(columns={"ONS Code": "la_code"})
    ct["band_d"] = pd.to_numeric(ct[incl], errors="coerce").fillna(
        pd.to_numeric(ct[excl], errors="coerce")
    )
    return ct.dropna(subset=["band_d"])[["la_code", "band_d"]]


def build() -> pd.DataFrame:
    ahc = load_ahc_by_la()
    ct = load_council_tax_by_code()
    factor = BILL_ASSUMPTIONS["council_tax_per_dwelling_factor"]

    df = ahc.merge(ct, on="la_code", how="left")
    df["ct_is_estimated"] = df["band_d"].isna()
    # Band D -> estimated average per dwelling; national fallback where absent.
    df["council_tax"] = (df["band_d"].fillna(NAT_AVG_BAND_D) * factor).round(0)

    residual = compute_residual(df["ahc_income"], df["council_tax"])
    df = pd.concat([df[["la_code", "la_name", "ct_is_estimated"]], residual], axis=1)
    return df


def attach_to_composite(residual_all: pd.DataFrame) -> None:
    comp_path = OUTPUT_DIR / "09_clpi_composite.csv"
    comp = pd.read_csv(comp_path)
    comp["_k"] = comp["la_name"].map(_norm)
    residual_all["_k"] = residual_all["la_name"].map(_norm)

    cols = [
        "ahc_income",
        "energy",
        "council_tax",
        "food",
        "transport",
        "residual_annual",
        "residual_weekly",
    ]
    # Drop any prior residual columns so re-runs are idempotent.
    comp = comp.drop(columns=[c for c in cols + ["score_residual"] if c in comp.columns])
    merged = comp.merge(residual_all[["_k"] + cols], on="_k", how="left")

    unmatched = merged.loc[merged["ahc_income"].isna(), "la_name"].tolist()
    if unmatched:
        print(f"  WARNING: no residual data for: {unmatched}")

    # Score within the composite set (relative 0-100, inverted).
    merged["score_residual"] = score_residual(merged["residual_annual"])
    merged = merged.drop(columns=["_k"])
    merged.to_csv(comp_path, index=False)
    print(f"  Updated {comp_path.name}: +{len(cols)+1} residual columns")


def main() -> int:
    print("Building residual income from ONS AHC + GOV.UK council tax ...")
    residual_all = build()
    out = OUTPUT_DIR / "16_residual_income_la.csv"
    residual_all.drop(columns=[c for c in ["_k"] if c in residual_all.columns]).to_csv(
        out, index=False
    )
    est = int(residual_all["ct_is_estimated"].sum())
    print(
        f"  Wrote {out.name}: {len(residual_all)} LAs "
        f"({est} with estimated council tax)"
    )
    attach_to_composite(residual_all)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
