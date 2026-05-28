"""
Covered Club UK market analysis — pipeline orchestrator.

Order of operations:
1. Ingest each source (IMD, fuel poverty, GDHI, postcode lookup,
   family spending, gambling).
2. Roll LSOA-level data up to LA level using the postcode lookup.
3. Compute CLPI per LA.
4. Compute affordability per income quintile.
5. Compute prize-vs-spend ratios.
6. Export everything to data/output/ for Tableau.

Run with:
    python run_pipeline.py
"""

from __future__ import annotations
import sys
import traceback

import pandas as pd

from src.ingest import (
    imd,
    fuel_poverty,
    gdhi,
    postcode_lookup,
    family_spending,
    gambling,
)
from src.ingest import census, universal_credit, premises, companies_house
from src.analyse import clpi as clpi_module, affordability, prize_value
from src.export import tableau
from config import OUTPUT_DIR


# A region lookup for joining GDHI to LAs. This is approximate; for v2,
# join via the official ITL1 lookup from the postcode directory.
LA_TO_REGION_HINTS = {
    "E06": "varies",  # unitary
    "E07": "varies",  # non-metropolitan district
    "E08": "varies",  # metropolitan district
    "E09": "London",  # London borough
}


def step(name: str):
    """Decorator-like helper for visual step logging."""
    print(f"\n{'='*70}\n{name}\n{'='*70}")


def main() -> int:
    # ---------- 1. INGEST ----------
    step("1. INGEST")

    try:
        imd_lsoa_df = imd.fetch()
        print(f"  IMD 2025: {len(imd_lsoa_df):,} LSOAs")
    except Exception as e:
        print(f"  IMD ingest failed: {e}")
        print("  Hint: fill in config.URLS['imd_2025'] with the real download URL")
        return 1

    try:
        fp_lsoa_df = fuel_poverty.fetch()
        print(f"  Fuel poverty: {len(fp_lsoa_df):,} LSOAs")
    except Exception as e:
        print(f"  Fuel poverty ingest failed: {e}")
        print("  Hint: fill in config.URLS['fuel_poverty_lsoa']")
        return 1

    try:
        pc_df = postcode_lookup.fetch()
        print(f"  Postcode directory: {len(pc_df):,} postcodes")
    except Exception as e:
        print(f"  Postcode directory ingest failed: {e}")
        print(
            "  Hint: fill in config.URLS['postcode_directory'] or place the "
            "CSV manually at data/raw/ons_postcode_directory.csv"
        )
        return 1

    gdhi_df = gdhi.fetch()
    print(f"  GDHI: {len(gdhi_df):,} regions")

    quintile_df = family_spending.fetch()
    print(f"  Family spending: {len(quintile_df):,} quintiles")

    gambling_df = gambling.fetch()
    print(f"  Gambling market: {len(gambling_df):,} metrics")

    # ---------- 2. ROLL UP TO LA ----------
    step("2. ROLL UP TO LOCAL AUTHORITY")

    imd_la_df = imd.la_summary(imd_lsoa_df)
    print(f"  IMD LA summary: {len(imd_la_df):,} LAs")

    lsoa_la_lookup = postcode_lookup.lsoa_to_la(pc_df)
    # Add LA names from the IMD summary
    lsoa_la_lookup = lsoa_la_lookup.merge(
        imd_la_df[["la_code", "la_name"]], on="la_code", how="left"
    )
    print(f"  LSOA->LA lookup: {len(lsoa_la_lookup):,} rows")

    fp_la_df = fuel_poverty.la_summary(fp_lsoa_df, lsoa_la_lookup)
    print(f"  Fuel poverty LA summary: {len(fp_la_df):,} LAs")

    # ---------- 3. BUILD CLPI ----------
    step("3. BUILD CLPI")

    # Join IMD + fuel poverty. We don't have a direct LA->region lookup
    # without enriching from the postcode directory, so for now we attach
    # the region from the IMD or fuel poverty data and fall back to UK avg
    # GDHI where region is missing.
    la_joined = imd_la_df.merge(
        fp_la_df[["la_code", "fuel_poor_pct"]], on="la_code", how="left"
    )

    # If you have a la_code -> region lookup, merge it in here. For v1 we
    # accept that the income_gap component will be 0 for LAs we can't map.
    la_joined["gdhi_per_head_gbp"] = gdhi_df.loc[
        gdhi_df["region"] == "UK", "gdhi_per_head_gbp"
    ].iloc[0]
    # NOTE: replace this with a real regional join in v2

    # Drop LAs with missing fuel poverty data (rare — typically <5 LAs)
    before = len(la_joined)
    la_joined = la_joined.dropna(subset=["fuel_poor_pct"])
    print(
        f"  LAs with complete data: {len(la_joined):,} (dropped {before - len(la_joined)})"
    )

    clpi_df = clpi_module.compute(la_joined)
    print(f"  CLPI computed for {len(clpi_df):,} LAs")
    print("\n  Top 10 CLPI ranked:")
    print(
        clpi_df[
            ["clpi_rank", "la_name", "la_rank_avg_rank", "fuel_poor_pct", "clpi_score"]
        ]
        .head(10)
        .to_string(index=False)
    )

    # ---------- 4. AFFORDABILITY ----------
    step("4. AFFORDABILITY BY QUINTILE")

    afford_df = affordability.compute(quintile_df)
    print(afford_df.to_string(index=False))

    # ---------- 5. PRIZE VALUE ----------
    step("5. PRIZE-vs-SPEND RATIOS")

    prize_df = prize_value.compute()
    print(prize_df.to_string(index=False))

    # ---------- 6. EXPORT ----------
    step("6. EXPORT TO TABLEAU CSVs")

    tableau.write_all(
        {
            "01_clpi_by_la": clpi_df,
            "02_affordability": afford_df,
            "03_prize_value": prize_df,
            "04_gambling_market": gambling_df,
            "05_gdhi_by_region": gdhi_df,
            "06_quintile_spend": quintile_df,
            "07_fuel_poverty_la": fp_la_df,
            "08_imd_la_summary": imd_la_df,
        }
    )

    # ---------- 7. DEMOGRAPHIC DATA ----------
    step("7. DEMOGRAPHIC DATA (Census 2021 + UC)")

    # 7a. Sex by LA
    sex_la_df = pd.DataFrame()
    try:
        sex_lsoa_df = census.fetch_sex_by_lsoa()
        if not sex_lsoa_df.empty:
            sex_la_df = census.sex_la_summary(sex_lsoa_df, lsoa_la_lookup)
            sex_la_df.to_csv(OUTPUT_DIR / "10_sex_by_la.csv", index=False)
            print(f"  Sex by LA: {len(sex_la_df):,} LAs")
        else:
            print("  Sex by LA: no data (NOMIS_API_KEY may not be set)")
    except Exception as e:
        print(f"  Sex by LA failed: {e}")

    # 7b. Household composition by LA
    household_la_df = pd.DataFrame()
    try:
        hh_lsoa_df = census.fetch_household_composition()
        if not hh_lsoa_df.empty:
            household_la_df = census.household_la_summary(hh_lsoa_df, lsoa_la_lookup)
            household_la_df.to_csv(
                OUTPUT_DIR / "11_household_composition_la.csv", index=False
            )
            print(f"  Household composition: {len(household_la_df):,} LAs")
        else:
            print("  Household composition: no data")
    except Exception as e:
        print(f"  Household composition failed: {e}")

    # 7c. Universal Credit claimants by sex
    uc_df = pd.DataFrame()
    try:
        uc_df = universal_credit.fetch()
        if not uc_df.empty:
            uc_df.to_csv(OUTPUT_DIR / "12_uc_claimants_by_sex_la.csv", index=False)
            print(f"  UC claimants: {len(uc_df):,} LAs")
        else:
            print("  UC claimants: no data")
    except Exception as e:
        print(f"  UC claimants failed: {e}")

    # ---------- 8. VENUE & GAMBLING PROPENSITY ----------
    step("8. VENUE & GAMBLING PROPENSITY DATA")

    # 8a. Gambling Commission premises register
    venues_df = pd.DataFrame()
    try:
        pc_la_lookup = pd.DataFrame()
        if "postcode" in pc_df.columns:
            pc_la_lookup = pc_df[["postcode", "la_code"]].copy()
            pc_la_lookup = pc_la_lookup.merge(
                imd_la_df[["la_code", "la_name"]], on="la_code", how="left"
            )
        venues_df = premises.fetch(
            postcode_la_lookup=pc_la_lookup if not pc_la_lookup.empty else None
        )
        if not venues_df.empty:
            print(f"  GC premises: {len(venues_df):,} LAs with venue data")
        else:
            print("  GC premises: no data (download may have failed)")
    except Exception as e:
        print(f"  GC premises failed: {e}")

    # 8b. Companies House leisure companies
    companies_df = pd.DataFrame()
    try:
        pc_la_lookup2 = pd.DataFrame()
        if "postcode" in pc_df.columns:
            pc_la_lookup2 = pc_df[["postcode", "la_code"]].copy()
            pc_la_lookup2 = pc_la_lookup2.merge(
                imd_la_df[["la_code", "la_name"]], on="la_code", how="left"
            )
        companies_df = companies_house.fetch(
            postcode_la_lookup=pc_la_lookup2 if not pc_la_lookup2.empty else None
        )
        if not companies_df.empty:
            print(
                f"  Companies House: {len(companies_df):,} LAs with leisure/gambling companies"
            )
        else:
            print("  Companies House: no data")
    except Exception as e:
        print(f"  Companies House failed: {e}")

    # 8c. Gambling spend by region
    try:
        gambling_spend_df = family_spending.fetch_gambling_spend()
        gambling_spend_df.to_csv(
            OUTPUT_DIR / "15_gambling_spend_by_region.csv", index=False
        )
        print(f"  Gambling spend by region: {len(gambling_spend_df):,} regions")
    except Exception as e:
        print(f"  Gambling spend by region failed: {e}")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
