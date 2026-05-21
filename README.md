# Covered Club UK Market Analysis

Pre-launch market analysis for Covered Club, a UK prize draw platform focused
on household bills. This pipeline ingests public UK statistics (MHCLG, DESNZ,
ONS, Gambling Commission), calculates a Cost-of-Living Pressure Index (CLPI)
per local authority, and outputs CSVs for Tableau dashboards.

## What this answers

1. **Where to launch** — top postcode districts by cost-of-living pressure
2. **Which prize to lead with** — bill category with most acute pain
3. **What to charge** — ticket affordability per income quintile

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in NOMIS_API_KEY if using Census v2
```

## Running

```bash
python run_pipeline.py
```

Outputs land in `data/output/` as CSVs, ready for Tableau.

You can also run any single ingest module directly to inspect its output:

```bash
python -m src.ingest.imd
python -m src.ingest.fuel_poverty
python -m src.ingest.gdhi
```

## Project structure

```
covered_club_analysis/
├── config.py              # paths, URLs, constants, CLPI weights
├── run_pipeline.py        # orchestrator
├── src/
│   ├── ingest/            # one module per data source
│   ├── clean/             # postcode/boundary normalisation
│   ├── analyse/           # CLPI, affordability, prize-vs-spend
│   └── export/            # write final CSVs for Tableau
└── data/
    ├── raw/               # downloads land here
    ├── interim/           # cleaned intermediate
    └── output/            # final CSVs for Tableau
```

## Data sources

| Source | Access | Module |
|---|---|---|
| MHCLG IoD 2025 | File download | `src/ingest/imd.py` |
| DESNZ Fuel Poverty 2026 | File download | `src/ingest/fuel_poverty.py` |
| ONS Family Spending FYE 2024 | File download | `src/ingest/family_spending.py` |
| ONS Regional GDHI 2023 | ONS Beta API + fallback | `src/ingest/gdhi.py` |
| ONS Postcode Directory | File download | `src/ingest/postcode_lookup.py` |
| Gambling Commission GSGB | Published figures | `src/ingest/gambling.py` |
| ONS Census 2021 | Nomis API (v2) | `src/ingest/census.py` |

## Configuration

`config.py` is the single source of truth for paths, URLs, constants and
CLPI weights. The default CLPI weighting is 50% deprivation, 25% fuel
poverty, 25% income gap. Change `CLPI_WEIGHTS` to re-weight.

## v2 roadmap

- Census 2021 demographic enrichment (age, household, ethnicity) via Nomis API
- DWP Stat-Xplore for Universal Credit at LSOA
- Once Covered Club launches: join first-party customer data, compute real
  CAC/LTV by postcode

## Manifest

Every download is logged to `data/manifest.csv` with timestamp, URL, file
size, and status. This is the audit trail for which datasets the pipeline
ran on.
