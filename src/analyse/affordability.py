"""
Per-quintile affordability calculation.

Question: can a ticket be bought without sacrificing essentials?

This is a theoretical capacity calculation, not a predicted-spend
calculation. It answers a yes/no question for responsible-gambling
positioning.
"""
from __future__ import annotations
import pandas as pd


def compute(
    quintile_df: pd.DataFrame,
    ticket_prices: list[int] | None = None,
) -> pd.DataFrame:
    """
    Adds affordability columns to the quintile spend DataFrame.

    quintile_df must have columns:
        quintile, total_weekly_gbp, pct_housing_fuel_power, pct_food

    For each ticket price, adds:
        ticket_{price}_as_pct_of_headroom

    Defaults to the three Covered Club ticket prices: £10, £15, £20.
    """
    if ticket_prices is None:
        ticket_prices = [10, 15, 20]

    out = quintile_df.copy()

    # Essentials = housing/fuel/power + food
    out["essentials_pct"] = out["pct_housing_fuel_power"] + out["pct_food"]
    out["essentials_weekly_gbp"] = (
        out["total_weekly_gbp"] * out["essentials_pct"] / 100
    ).round(2)
    out["non_essential_weekly_gbp"] = (
        out["total_weekly_gbp"] - out["essentials_weekly_gbp"]
    ).round(2)

    # For each ticket price, what fraction of weekly headroom does it eat?
    for price in ticket_prices:
        col = f"ticket_{price}gbp_as_pct_of_headroom"
        out[col] = (price / out["non_essential_weekly_gbp"] * 100).round(1)

    # Theoretical max tickets per week at each price point
    for price in ticket_prices:
        col = f"theoretical_max_{price}gbp_tickets_weekly"
        out[col] = (out["non_essential_weekly_gbp"] / price).round(1)

    return out
