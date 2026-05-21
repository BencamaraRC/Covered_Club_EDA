# Data sources — where to find them

Quick reference for filling in `config.URLS` and manually downloading any
files that the pipeline can't fetch automatically.

## MHCLG English Indices of Deprivation 2025

- **Landing page**: https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025
- **What to grab**: File 1 (IMD ranks + deciles by LSOA), Excel
- **Released**: 30 October 2025
- **Where to put it**: `data/raw/imd_2025.xlsx`
- **Config key**: `URLS["imd_2025"]`

## DESNZ Sub-regional Fuel Poverty 2026

- **Landing page**: https://www.gov.uk/government/statistics/sub-regional-fuel-poverty-report-2026-2024-data
- **What to grab**: Sub-regional tables, Excel — Table 4 (LSOA level)
- **Released**: 14 May 2026
- **Where to put it**: `data/raw/fuel_poverty_2024.xlsx`
- **Config key**: `URLS["fuel_poverty_lsoa"]`

## ONS Family Spending FYE 2024

- **Landing page**: https://www.ons.gov.uk/peoplepopulationandcommunity/personalandhouseholdfinances/expenditure/bulletins/familyspendingintheuk/april2023tomarch2024
- **What to grab**: Workbook 3 (expenditure by region), Excel
- **Released**: 10 September 2025
- **Where to put it**: `data/raw/family_spending_2024.xlsx`
- **Config key**: `URLS["family_spending_workbook3"]`

## ONS Regional GDHI 2023

- **Landing page**: https://www.ons.gov.uk/economy/regionalaccounts/grossdisposablehouseholdincome/bulletins/regionalgrossdisposablehouseholdincomegdhi/latest
- **Access method**: ONS Beta API (preferred) or download Excel
- **Released**: September 2025
- **Where to put it**: pipeline uses hardcoded fallback if API fails

## ONS Postcode Directory

- **Landing page**: https://geoportal.statistics.gov.uk/
- **Search**: "ONS Postcode Directory" — pick the latest version
- **What to grab**: the main CSV (~1.4GB)
- **Where to put it**: `data/raw/ons_postcode_directory.csv`
- **Alternative**: National Statistics Postcode Lookup (NSPL) is the
  same data minus the boundary geometries, smaller download
- **Config key**: `URLS["postcode_directory"]`

## Gambling Commission GSGB

- **Landing page**: https://www.gamblingcommission.gov.uk/statistics-and-research/statistics
- **What to grab**: latest GSGB wave publication, headline data
- **Note**: figures are hardcoded in `src/ingest/gambling.py` because
  there's no machine-readable feed for the headline stats

## DCMS PDC Market Study 2025

- **URL**: https://www.gov.uk/government/publications/research-report-online-prize-draws-and-competitions-market-study-assessment-of-harm-and-review-of-potential-interventions
- **Released**: 26 June 2025
- **Note**: a report PDF, not a dataset. Key figures (£1.3bn market,
  7.4m participants, 88% gambling overlap) are hardcoded in
  `src/ingest/gambling.py`

## Nomis API (Census 2021) — v2 only

- **Landing page**: https://www.nomisweb.co.uk/
- **Sign up**: free API key
- **Datasets to start with**:
  - TS002 — Age by single year (`NM_2010_1`)
  - TS003 — Household composition (`NM_2026_1`)
  - TS021 — Ethnic group (`NM_2027_1`)
- **API docs**: https://www.nomisweb.co.uk/api/v01/help
