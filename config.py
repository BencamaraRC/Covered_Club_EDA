"""
Central config: paths, URLs, constants, CLPI weights.
Edit here, not in the modules.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# ============ PATHS ============
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
OUTPUT_DIR = DATA_DIR / "output"

for d in (RAW_DIR, INTERIM_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ============ CLPI WEIGHTS ============
# Composite score = w_dep * deprivation + w_fp * fuel_poverty + w_inc * income_gap
# Defaults: deprivation dominates because IMD already encodes 7 sub-domains.
# Change here if you want fuel poverty weighted more heavily.
CLPI_WEIGHTS = {
    "deprivation": 0.50,
    "fuel_poverty": 0.25,
    "income_gap": 0.25,
}

# ============ DATA SOURCE URLS ============
# Verify each URL when first running — gov.uk filenames change between releases.
# If a URL 404s, visit the relevant statistics landing page to grab the new one:
#   https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025
#   https://www.gov.uk/government/statistics/sub-regional-fuel-poverty-report-2026-2024-data
URLS = {
    "imd_2025": (
        "https://assets.publishing.service.gov.uk/media/"
        "691dece32c6b98ecdbc500d5/File_1_IoD2025_Index_of_Multiple_Deprivation.xlsx"  # File 1: IMD ranks + deciles by LSOA
    ),
    "fuel_poverty_lsoa": (
        "https://assets.publishing.service.gov.uk/media/"
        "69c3b17f3ed0546101e0dc45/2024_Detailed_Tables__2026_Fuel_Poverty_Statistics_Publication_.xlsx"  # Sub-regional fuel poverty 2026, Table 4 LSOA
    ),
    "family_spending_workbook3": (
        "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/"
        "personalandhouseholdfinances/expenditure/datasets/"
        "familyspendingworkbook3expenditurebyregion/april2023tomarch2024/"
        "familyspendingworkbook3expenditurebyregion.xlsx"
    ),
    "postcode_directory": (
        "https://geoportal.statistics.gov.uk/datasets/ons::ons-postcode-directory-may-2025-uk/about"  # ONS Postcode Directory May 2025
    ),
    "gambling_gsgb": (
        "https://www.gamblingcommission.gov.uk/statistics-and-research/publication/"
        "GET_LATEST_WAVE_FROM_GC_WEBSITE"
    ),
}

# ============ API CONFIG ============
ONS_API_BASE = os.getenv("ONS_API_BASE", "https://api.beta.ons.gov.uk/v1")
NOMIS_API_KEY = os.getenv("NOMIS_API_KEY", "")

# ============ CONSTANTS ============
UK_AVG_GDHI_2023 = 24836  # £ per head, ONS Sep 2025 release
TOTAL_ENGLISH_LSOAS = 33755  # IoD 2025
TOTAL_ENGLISH_LAS = 296  # IoD 2025

# UK average weekly household spend by category (ONS Family Spending FYE 2024).
# Used for prize-vs-spend ratios.
UK_AVG_WEEKLY_SPEND = {
    "food": 70.50,
    "energy": 40.50,
    "petrol": 21.40,
    "housing_fuel_power_total": 113.30,
    "transport_total": 88.20,
}

# ============ RESIDUAL-INCOME ("after bills") MODEL ============
# residual = net income After Housing Costs (per LA, real)
#            − energy − council tax (per LA, real) − food − transport
# Water is NOT subtracted: ONS "After Housing Costs" already nets out water
# charges, so subtracting it again would double-count.
#
# Energy/food/transport are standardised NATIONAL annual £ assumptions (they
# shift every LA by the same amount); the LA-to-LA differences come from the
# real local AHC income + council tax. All figures are auditable here.
BILL_ASSUMPTIONS = {
    "energy_annual_gbp": 1700,  # Ofgem price cap, typical dual-fuel household 2024-25
    "food_annual_gbp": round(70.50 * 52),  # ONS Family Spending FYE2024 food
    "transport_annual_gbp": round(88.20 * 52),  # ONS Family Spending FYE2024 transport
    # Council tax is per-LA (GOV.UK Table 7). Band D is scaled to an average
    # per-dwelling basis because most homes in deprived areas sit in Bands A-C
    # and pay less than Band D (national avg per dwelling ÷ avg Band D, 2024-25).
    "council_tax_per_dwelling_factor": 1668 / 2171,
}

# Covered Club prize structure (from business overview).
COVERED_CLUB_PRIZES = [
    {
        "competition": "Food Shop Friday",
        "ticket_gbp": 20,
        "prize_gbp": 7800,
        "category": "food",
    },
    {
        "competition": "Heating Help",
        "ticket_gbp": 10,
        "prize_gbp": 2500,
        "category": "energy",
    },
    {
        "competition": "Fuel Covered",
        "ticket_gbp": 10,
        "prize_gbp": 2500,
        "category": "petrol",
    },
    {
        "competition": "Childcare Covered",
        "ticket_gbp": 15,
        "prize_gbp": 5000,
        "category": "childcare",
    },
]
