"""
Prize-vs-spend ratios.

For each Covered Club prize, calculate:
    annual_category_spend_gbp = UK average weekly spend on category * 52
    prize_as_pct_of_annual    = prize / annual_category_spend * 100
    ticket_vs_weekly_pain_pct = ticket / weekly_category_spend * 100

The first ratio drives the "value framing" message in marketing
(e.g. "win 2x what you spend on food in a year").
The second ratio sanity-checks whether the ticket price is meaningful
relative to the bill it covers.
"""
from __future__ import annotations
import pandas as pd

from config import COVERED_CLUB_PRIZES, UK_AVG_WEEKLY_SPEND


def compute() -> pd.DataFrame:
    """
    Returns one row per Covered Club prize with calculated ratios.

    Childcare is included for completeness but has no LCF average — the
    weekly_category_spend field is NaN. Add a real figure once you've
    sourced an average UK childcare cost.
    """
    rows = []
    for prize in COVERED_CLUB_PRIZES:
        cat = prize["category"]
        weekly = UK_AVG_WEEKLY_SPEND.get(cat)

        row = {
            "competition":        prize["competition"],
            "ticket_gbp":         prize["ticket_gbp"],
            "prize_gbp":          prize["prize_gbp"],
            "category":           cat,
            "weekly_avg_uk_gbp":  weekly,
        }

        if weekly is not None:
            annual = weekly * 52
            row["annual_category_spend_gbp"] = round(annual, 0)
            row["prize_as_pct_of_annual"] = round(prize["prize_gbp"] / annual * 100, 0)
            row["ticket_vs_weekly_pain_pct"] = round(prize["ticket_gbp"] / weekly * 100, 1)
        else:
            row["annual_category_spend_gbp"] = None
            row["prize_as_pct_of_annual"] = None
            row["ticket_vs_weekly_pain_pct"] = None

        rows.append(row)

    return pd.DataFrame(rows)
