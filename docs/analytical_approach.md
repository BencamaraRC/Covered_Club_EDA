# Analytical Approach

This analysis uses published UK statistics only. No first-party Covered Club
customer data exists pre-launch, so the approach is to triangulate the
answers from official sources, calculate a composite pressure score per
area, and pressure-test the proposed prizes and ticket prices against the
resulting target audience.

## Geographic unit

The unit of analysis is the **Lower-layer Super Output Area (LSOA)** — a
small UK statistical area of roughly 1,500 residents. LSOAs are the level
at which the MHCLG Indices of Deprivation are published, and they roll up
cleanly to local authority and postcode district. Outputs for marketing use
are presented at **postcode district level** (the first half of a postcode,
e.g. `B19` or `FY1`), which is how UK paid-media platforms accept
geo-targeting.

Why not the literal postcode level requested in the brief: several of the
questions (gambling spend, political views, smoking prevalence) are not
published at full postcode level and cannot be without commercial data
purchase. LSOA → postcode district is the closest reliable substitute.

## Data sources matrix

| Question | Primary source | Granularity | Access method |
|---|---|---|---|
| Which areas struggle most with cost of living? | MHCLG Indices of Deprivation 2025 (Oct 2025) | LSOA → LA | File download (gov.uk) |
| Demographic profile of target areas | ONS Census 2021 | LSOA / OA | Nomis API (v2) |
| Welfare reliance | DWP Stat-Xplore (Universal Credit) | LSOA / LA | Stat-Xplore API (v2) |
| Postcode ↔ LSOA mapping | ONS Postcode Directory | Postcode | File download (ONS) |
| Fuel poverty | DESNZ Sub-regional fuel poverty 2026 (May 2026) | LSOA → LA → Region | File download (gov.uk) |
| Household spend by category | ONS Family Spending FYE 2024 | UK + quintile + region | File download (ONS) |
| Disposable income | ONS Regional GDHI 2023 | ITL1 region | ONS Beta API + fallback |
| Gambling participation | Gambling Commission GSGB 2024-25 | GB-wide | Published figures |
| Prize draw market | DCMS / London Economics PDC Study 2025 | UK | Published figures |

## Out of scope and why

- **Postcode-level gambling spend** is not published by any UK government
  source. The GSGB gives GB-wide and demographic breakdowns only. Regional
  gambling spend would require commercial data (e.g. Mintel, CACI) and is
  excluded from v1.
- **Political party views by postcode** are not collected at this
  granularity. The closest available is constituency-level voting data
  (House of Commons Library), which we are not joining for v1.
- **Smoking prevalence** is published at local authority level via OHID
  Fingertips, not postcode. It is excluded from the composite but flagged
  for later inclusion if needed for ad-creative tone.

## Cleaning rules

1. **Postcode normalisation**: strip whitespace, uppercase, split into
   postcode area (e.g. `B`) and district (e.g. `B19`) via the first half
   of the postcode.
2. **Boundary alignment**: IoD 2025 uses 2021 Census LSOA boundaries
   (33,755 LSOAs); ensure all joins use the same boundary version. Older
   datasets on 2011 boundaries are remapped using the ONS LSOA 2011→2021
   lookup.
3. **Missing values**: where an LA does not appear in the published top-20
   fuel poverty list, the regional fuel poverty rate is used as a fallback
   (flagged in a `data_source` column).
4. **Outliers**: none expected in official statistics, but a sanity check
   on each input (e.g. fuel poverty between 0 and 100, GDHI within
   £10k–£100k per head).
5. **Inflation adjustment**: not applied. All figures are kept in their
   published year (£FYE 2024 for spend, £2023 for GDHI, 2024 data for
   fuel poverty). The report makes the year of each figure explicit.
6. **Quintile interpolation**: ONS publishes Q1 (£378.60) and Q5 (£948.70)
   total weekly spend but not Q2–Q4. Where intermediate values are needed,
   they are interpolated linearly and flagged as estimates.

## The Cost-of-Living Pressure Index (CLPI)

The CLPI is a composite score per LA, calculated as:

```
CLPI = 0.50 × score_deprivation
     + 0.25 × score_fuel_poverty
     + 0.25 × score_income_gap
```

Where:

- `score_deprivation` = (296 − IMD 2025 average score rank) ÷ 296 × 100.
  Inverts the rank so higher = more deprived.
- `score_fuel_poverty` = LA fuel poverty rate ÷ max(fuel poverty rate)
  × 100. Normalises to a 0-100 scale.
- `score_income_gap` = max(0, (UK average GDHI − LA region GDHI)
  ÷ UK average GDHI × 100). Zero for above-average regions.

The 50/25/25 weighting reflects that deprivation is the most comprehensive
single measure (it already incorporates seven sub-domains including income
and employment), while fuel poverty and income gap add specificity to the
cost-of-living dimension that Covered Club specifically addresses.

CLPI outputs are ranked from highest (most pressure, best target market)
to lowest (least pressure, deprioritise).

## Affordability calculation

Per quintile, the calculation is:

```
non_essential_weekly_£ = total_weekly_spend × (1 − essentials_pct)
```

Where `essentials_pct` = (housing/fuel/power share) + (food share).
Non-essential weekly £ is the theoretical headroom for a Covered Club
ticket purchase. A £10 ticket is then evaluated as a percentage of this
headroom (e.g. Q1: £10 ÷ £230.95 = 4.3%).

This is a **theoretical capacity** calculation, not a predicted-spend
calculation. It answers "can this customer afford the ticket without
sacrificing essentials" — a yes/no question for responsible-gambling
positioning.

## Prize-vs-spend ratios

Per prize, the calculation is:

```
prize_as_pct_of_annual_spend = prize_£ ÷ (weekly_category_spend × 52) × 100
```

Where `weekly_category_spend` is the UK average from the ONS LCF (e.g.
£70.50 for food, £40.50 for energy, £21.40 for petrol). This produces the
"value framing" figure used to prioritise which prize leads acquisition
campaigns (e.g. Food Shop Friday at 213% means the prize is worth 2.13×
annual spend on the category).

## Limitations

- **No live customer data**: every recommendation is from published
  statistics. Real conversion rates, CAC by postcode, and LTV will need
  4–6 weeks of post-launch data to validate or revise the targeting.
- **Quintile spend is UK-wide, not LA-specific**: Q1 spend in Blackpool
  may differ from Q1 spend in Birmingham, but the LCF sample isn't large
  enough to break out by LA.
- **PDC market sizing is GB-wide**: 7.4m participants and £1.3bn annual
  spend are national totals (DCMS, 2025). We cannot say what share comes
  from the target postcodes without first-party data.
- **No segmentation by household composition pre-launch**: the report
  assumes the persona is "working-age, household with children, low-to-mid
  income" based on the IoD 2025 income domain. This will be confirmed or
  refined by Census 2021 demographic joins in v2.
