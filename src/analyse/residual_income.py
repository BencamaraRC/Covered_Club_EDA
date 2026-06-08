"""
Residual household income — "money left after the bills".

residual = net income After Housing Costs (per LA)
           − energy − council tax − food − transport

This replaces the old GDHI-per-head income component, which was income
*before* bills, *per person*, smeared by region. Residual income is per
Local Authority and built from real local data (ONS small-area AHC income +
GOV.UK council tax) with standardised national bill assumptions for the rest.

Water is deliberately NOT subtracted: ONS "After Housing Costs" already nets
out water charges, so subtracting again would double-count.

Higher residual = more headroom = less pressure.
The residual SCORE (0-100) inverts this so 100 = least headroom = most
pressure, matching the polarity of the other CLPI component scores.

See config.BILL_ASSUMPTIONS for the auditable bill figures.
"""
from __future__ import annotations
import pandas as pd

from config import BILL_ASSUMPTIONS


def compute_residual(
    ahc_income: pd.Series,
    council_tax: pd.Series,
) -> pd.DataFrame:
    """
    Build the annual residual and its weekly equivalent from per-LA AHC income
    and per-LA council tax. Energy/food/transport come from BILL_ASSUMPTIONS.

    Returns a DataFrame with one column per bill plus residual_annual /
    residual_weekly, indexed like the inputs.
    """
    b = BILL_ASSUMPTIONS
    out = pd.DataFrame(index=ahc_income.index)
    out["ahc_income"] = ahc_income.round(0)
    out["energy"] = b["energy_annual_gbp"]
    out["council_tax"] = council_tax.round(0)
    out["food"] = b["food_annual_gbp"]
    out["transport"] = b["transport_annual_gbp"]
    out["residual_annual"] = (
        out["ahc_income"]
        - out["energy"]
        - out["council_tax"]
        - out["food"]
        - out["transport"]
    ).round(0)
    out["residual_weekly"] = (out["residual_annual"] / 52).round(0)
    return out


def score_residual(residual_annual: pd.Series) -> pd.Series:
    """
    Normalise residual income to a 0-100 pressure score (min-max, inverted)
    across the supplied set of LAs: lowest residual -> 100 (most pressure),
    highest -> 0. Mirrors the 0-100 polarity of score_deprivation /
    score_fuel_poverty in src/analyse/clpi.py.
    """
    r = residual_annual.astype(float)
    spread = r.max() - r.min()
    if spread == 0:
        return pd.Series([0.0] * len(r), index=r.index)
    return ((r.max() - r) / spread * 100).round(1)
