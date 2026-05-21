"""
Shared cleaning helpers. Keep all string normalisation and boundary
alignment here so the rules in the Analytical Approach are enforced
in one place.
"""
from __future__ import annotations
import pandas as pd


def normalise_postcode(s: pd.Series) -> pd.Series:
    """Strip whitespace, uppercase. 'sw1a 1aa' -> 'SW1A1AA'."""
    return s.astype(str).str.replace(r"\s+", "", regex=True).str.upper()


def extract_district(postcode: pd.Series) -> pd.Series:
    """
    Extract postcode district (outward code).
        'SW1A1AA' -> 'SW1A'
        'B193NJ'  -> 'B19'
    Logic: the outward code is everything before the inward code (last 3 chars).
    """
    pc = normalise_postcode(postcode)
    return pc.str[:-3]


def sanity_check_range(s: pd.Series, lo: float, hi: float, name: str) -> None:
    """Raise ValueError if values fall outside the expected range."""
    bad = s[(s < lo) | (s > hi)]
    if len(bad) > 0:
        raise ValueError(
            f"{name}: {len(bad)} values outside [{lo}, {hi}]. "
            f"Sample: {bad.head().tolist()}"
        )


def check_unique(df: pd.DataFrame, key: str) -> None:
    """Raise if the key column has duplicates."""
    dupes = df[df.duplicated(subset=[key], keep=False)]
    if len(dupes) > 0:
        raise ValueError(
            f"Expected {key} to be unique, found {len(dupes)} duplicates. "
            f"Sample: {dupes[key].head().tolist()}"
        )
