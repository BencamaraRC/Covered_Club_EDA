"""
Gambling Commission Gambling Survey for Great Britain (GSGB) 2024-25 +
DCMS / London Economics PDC Market Study 2025.

Note: GSGB does not publish postcode-level data. Returns GB-wide and
demographic breakdowns only. Used for context in the report, not joined
into the CLPI.
"""
from __future__ import annotations
import pandas as pd


def fetch(force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns headline GSGB + DCMS PDC stats.

    Hardcoded from published reports because there's no machine-readable
    feed for these figures. Each row carries its source for traceability.
    """
    return pd.DataFrame([
        {"metric": "Adults gambling in last 4 weeks (incl. lottery)",
         "value": 0.48,  "unit": "%", "source": "GC GSGB Y2 W3 2024"},
        {"metric": "Adults gambling excl. lottery-only",
         "value": 0.28,  "unit": "%", "source": "GC GSGB Y2 W3 2024"},
        {"metric": "Adults playing National Lottery",
         "value": 0.31,  "unit": "%", "source": "GC GSGB Y2 W3 2024"},
        {"metric": "Adults playing scratchcards",
         "value": 0.13,  "unit": "%", "source": "GC GSGB Y2 W3 2024"},
        {"metric": "Adults playing online instant-win",
         "value": 0.08,  "unit": "%", "source": "GC GSGB Y2 W3 2024"},
        {"metric": "Adults in prize draws/competitions annually",
         "value": 7.4e6, "unit": "n", "source": "DCMS / London Economics 2025"},
        {"metric": "Annual PDC market value",
         "value": 1.3e9, "unit": "gbp", "source": "DCMS / London Economics 2025"},
        {"metric": "PDC participants who also gamble or play lottery",
         "value": 0.88,  "unit": "%", "source": "DCMS 2025"},
    ])


if __name__ == "__main__":
    print(fetch())
