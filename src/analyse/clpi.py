"""
Cost-of-Living Pressure Index (CLPI).

CLPI = w_dep * score_deprivation
     + w_fp  * score_fuel_poverty
     + w_inc * score_income_gap

All three component scores are normalised to 0-100 (higher = more pressure).
Weights live in config.CLPI_WEIGHTS.

Higher CLPI = more pressure = better target market for Covered Club.
"""
from __future__ import annotations
import pandas as pd

from config import CLPI_WEIGHTS, TOTAL_ENGLISH_LAS, UK_AVG_GDHI_2023


def score_deprivation(la_rank: pd.Series) -> pd.Series:
    """
    Invert the IMD LA rank so higher = more deprived.
    Input: la_rank where 1 = most deprived (MHCLG convention).
    Output: 0-100 score where 100 = most deprived.
    """
    return (TOTAL_ENGLISH_LAS - la_rank) / TOTAL_ENGLISH_LAS * 100


def score_fuel_poverty(fp_pct: pd.Series) -> pd.Series:
    """
    Normalise to 0-100 by dividing by the max observed value.
    Input: fuel poverty rate as a percentage (e.g. 13.9 for Blackpool).
    """
    max_fp = fp_pct.max()
    if max_fp == 0:
        return pd.Series([0] * len(fp_pct), index=fp_pct.index)
    return fp_pct / max_fp * 100


def score_income_gap(region_gdhi: pd.Series) -> pd.Series:
    """
    Positive gap = below UK average = more pressure.
    Above UK average regions score 0 (no pressure from low income).
    """
    gap = (UK_AVG_GDHI_2023 - region_gdhi) / UK_AVG_GDHI_2023 * 100
    return gap.clip(lower=0)


def compute(
    la_df: pd.DataFrame,
    fp_col: str = "fuel_poor_pct",
    rank_col: str = "la_rank_avg_rank",
    gdhi_col: str = "gdhi_per_head_gbp",
) -> pd.DataFrame:
    """
    Adds clpi_score and clpi_rank columns to la_df.

    la_df must have at minimum:
        - la_code, la_name
        - rank_col (default: la_rank_avg_rank)
        - fp_col (default: fuel_poor_pct)
        - gdhi_col (default: gdhi_per_head_gbp)
    """
    out = la_df.copy()
    out["score_deprivation"]  = score_deprivation(out[rank_col])
    out["score_fuel_poverty"] = score_fuel_poverty(out[fp_col])
    out["score_income_gap"]   = score_income_gap(out[gdhi_col])

    w = CLPI_WEIGHTS
    out["clpi_score"] = (
        w["deprivation"]  * out["score_deprivation"]  +
        w["fuel_poverty"] * out["score_fuel_poverty"] +
        w["income_gap"]   * out["score_income_gap"]
    ).round(1)

    out = out.sort_values("clpi_score", ascending=False).reset_index(drop=True)
    out["clpi_rank"] = out.index + 1
    return out
