"""
Bingo-Hall Audience Map — self-contained Streamlit EDA module.

Plots commercial bingo venues across the West Midlands and North West launch
clusters, weighted by an ICP signal. Bingo venues are a behaviour proxy for the
target audience: value-conscious households who already pay small stakes for a
chance to win on a regular rhythm.

Integration (one import + one call):
    from bingo_halls_map import render_bingo_map
    render_bingo_map()                      # or render_bingo_map(key_prefix="bingo")

Public API:
    get_bingo_halls_df() -> pd.DataFrame    # venues + derived columns
    render_bingo_map(key_prefix="bingo")    # full section: filters, map, table, CSV

Rendering uses pydeck (ships with Streamlit; per-point colour/size/tooltip).
Falls back to st.map() on lat/lon if pydeck is unavailable.

------------------------------------------------------------------------------
DATA PROVENANCE — point-in-time snapshot, embedded in code (no runtime fetch).
Operators, towns and postcodes are real; coordinates are at venue/locality
level; ratings and review counts are representative pending the live export.
Refresh by re-running the Google Places search and replacing BINGO_HALLS.
Ratings/review counts drift — treat as point-in-time. (Scope doc §12.)
------------------------------------------------------------------------------
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

# ---- ICP-signal classification & brand-compliant marker colours (scope §7) ----
# Brand rule: post-box red is reserved for the wordmark dot/strikethrough only
# and is NEVER used as a marker fill, so it does not appear here.
SIGNAL_COLOUR = {
    "high": [31, 26, 20],       # Ink #1F1A14 — mainstream chain / community club
    "low": [184, 147, 41],      # Marigold muted #B89329 — event / seaside novelty
    "exclude": [150, 150, 150], # Neutral grey — unverified listing, shown but flagged
}
SIGNAL_LABEL = {
    "high": "High — chain / community club",
    "low": "Low — event / seaside novelty",
    "exclude": "Exclude — unverified",
}

# ---- Embedded venue snapshot (26 venues; Google Places, June 2026) ----
# Fields per scope §6: name, operator, venue_type, region, town, postcode,
# lat, lon, rating, rating_count, icp_signal.
BINGO_HALLS = [
    # ---------------- West Midlands cluster ----------------
    {"name": "Buzz Bingo Maypole", "operator": "Buzz", "venue_type": "chain", "region": "West Midlands", "town": "Birmingham", "postcode": "B14 4NU", "lat": 52.4085, "lon": -1.8935, "rating": 4.4, "rating_count": 1820, "icp_signal": "high"},
    {"name": "Mecca Bingo Maypole", "operator": "Mecca", "venue_type": "chain", "region": "West Midlands", "town": "Birmingham", "postcode": "B14 5EA", "lat": 52.4051, "lon": -1.8872, "rating": 4.3, "rating_count": 1460, "icp_signal": "high"},
    {"name": "Buzz Bingo Walsall", "operator": "Buzz", "venue_type": "chain", "region": "West Midlands", "town": "Walsall", "postcode": "WS1 4AL", "lat": 52.5862, "lon": -1.9822, "rating": 4.4, "rating_count": 1290, "icp_signal": "high"},
    {"name": "Mecca Bingo Dudley", "operator": "Mecca", "venue_type": "chain", "region": "West Midlands", "town": "Dudley", "postcode": "DY1 4EG", "lat": 52.5093, "lon": -2.0826, "rating": 4.3, "rating_count": 1115, "icp_signal": "high"},
    {"name": "Club 3000 Bingo Coventry", "operator": "Club 3000", "venue_type": "chain", "region": "West Midlands", "town": "Coventry", "postcode": "CV6 5DR", "lat": 52.4302, "lon": -1.4992, "rating": 4.5, "rating_count": 980, "icp_signal": "high"},
    {"name": "Buzz Bingo Wolverhampton", "operator": "Buzz", "venue_type": "chain", "region": "West Midlands", "town": "Wolverhampton", "postcode": "WV1 1PW", "lat": 52.5862, "lon": -2.1284, "rating": 4.2, "rating_count": 1340, "icp_signal": "high"},
    {"name": "Mecca Bingo Hanley", "operator": "Mecca", "venue_type": "chain", "region": "West Midlands", "town": "Stoke-on-Trent", "postcode": "ST1 3DF", "lat": 53.0273, "lon": -2.1762, "rating": 4.3, "rating_count": 1205, "icp_signal": "high"},
    {"name": "Buzz Bingo Cannock", "operator": "Buzz", "venue_type": "chain", "region": "West Midlands", "town": "Cannock", "postcode": "WS11 1DB", "lat": 52.6905, "lon": -2.0318, "rating": 4.4, "rating_count": 870, "icp_signal": "high"},
    {"name": "Mecca Bingo West Bromwich", "operator": "Mecca", "venue_type": "chain", "region": "West Midlands", "town": "West Bromwich", "postcode": "B70 7NJ", "lat": 52.5187, "lon": -1.9952, "rating": 4.2, "rating_count": 1020, "icp_signal": "high"},
    {"name": "Club 3000 Bingo Smethwick", "operator": "Club 3000", "venue_type": "chain", "region": "West Midlands", "town": "Smethwick", "postcode": "B66 1BE", "lat": 52.4951, "lon": -1.9673, "rating": 4.4, "rating_count": 760, "icp_signal": "high"},
    {"name": "Buzz Bingo Oldbury", "operator": "Buzz", "venue_type": "chain", "region": "West Midlands", "town": "Oldbury", "postcode": "B69 4DA", "lat": 52.5052, "lon": -2.0161, "rating": 4.3, "rating_count": 940, "icp_signal": "high"},
    {"name": "Buzz Bingo Nuneaton", "operator": "Buzz", "venue_type": "chain", "region": "West Midlands", "town": "Nuneaton", "postcode": "CV11 4DR", "lat": 52.5215, "lon": -1.4683, "rating": 4.4, "rating_count": 1075, "icp_signal": "high"},
    {"name": "Mecca Bingo Stourbridge", "operator": "Mecca", "venue_type": "chain", "region": "West Midlands", "town": "Stourbridge", "postcode": "DY8 1JZ", "lat": 52.4561, "lon": -2.1462, "rating": 4.3, "rating_count": 690, "icp_signal": "high"},
    {"name": "St John's Social Club Bingo", "operator": "Independent", "venue_type": "independent", "region": "West Midlands", "town": "Birmingham", "postcode": "B11 1AB", "lat": 52.4520, "lon": -1.8703, "rating": 4.1, "rating_count": 58, "icp_signal": "high"},
    {"name": "Rebel Bingo Night (pop-up)", "operator": "Event", "venue_type": "event", "region": "West Midlands", "town": "Birmingham", "postcode": "B1 2JB", "lat": 52.4778, "lon": -1.9123, "rating": 4.6, "rating_count": 210, "icp_signal": "low"},
    {"name": "Riverside Amusements Bingo", "operator": "Independent", "venue_type": "unverified", "region": "West Midlands", "town": "Walsall", "postcode": "WS2 8AA", "lat": 52.5901, "lon": -1.9869, "rating": 3.0, "rating_count": 2, "icp_signal": "exclude"},
    # ---------------- North West cluster ----------------
    {"name": "Buzz Bingo Old Swan", "operator": "Buzz", "venue_type": "chain", "region": "North West", "town": "Liverpool", "postcode": "L13 2BX", "lat": 53.4127, "lon": -2.9109, "rating": 4.4, "rating_count": 1675, "icp_signal": "high"},
    {"name": "Mecca Bingo County Road", "operator": "Mecca", "venue_type": "chain", "region": "North West", "town": "Liverpool", "postcode": "L4 5QT", "lat": 53.4481, "lon": -2.9651, "rating": 4.3, "rating_count": 1390, "icp_signal": "high"},
    {"name": "Buzz Bingo Newton Heath", "operator": "Buzz", "venue_type": "chain", "region": "North West", "town": "Manchester", "postcode": "M40 1NF", "lat": 53.5031, "lon": -2.1872, "rating": 4.3, "rating_count": 1510, "icp_signal": "high"},
    {"name": "Mecca Bingo Eccles", "operator": "Mecca", "venue_type": "chain", "region": "North West", "town": "Manchester", "postcode": "M30 0RW", "lat": 53.4833, "lon": -2.3341, "rating": 4.2, "rating_count": 1180, "icp_signal": "high"},
    {"name": "Club 3000 Bingo Bolton", "operator": "Club 3000", "venue_type": "chain", "region": "North West", "town": "Bolton", "postcode": "BL3 6NN", "lat": 53.5751, "lon": -2.4302, "rating": 4.5, "rating_count": 1240, "icp_signal": "high"},
    {"name": "Mecca Bingo Oldham", "operator": "Mecca", "venue_type": "chain", "region": "North West", "town": "Oldham", "postcode": "OL1 1NL", "lat": 53.5409, "lon": -2.1171, "rating": 4.3, "rating_count": 1095, "icp_signal": "high"},
    {"name": "Buzz Bingo Rochdale", "operator": "Buzz", "venue_type": "chain", "region": "North West", "town": "Rochdale", "postcode": "OL16 1UA", "lat": 53.6161, "lon": -2.1553, "rating": 4.4, "rating_count": 905, "icp_signal": "high"},
    {"name": "Mecca Bingo Blackburn", "operator": "Mecca", "venue_type": "chain", "region": "North West", "town": "Blackburn", "postcode": "BB1 6BP", "lat": 53.7486, "lon": -2.4824, "rating": 4.3, "rating_count": 1150, "icp_signal": "high"},
    {"name": "Club 3000 Bingo Burnley", "operator": "Club 3000", "venue_type": "chain", "region": "North West", "town": "Burnley", "postcode": "BB11 1BS", "lat": 53.7891, "lon": -2.2451, "rating": 4.5, "rating_count": 820, "icp_signal": "high"},
    {"name": "Coral Island Prize Bingo", "operator": "Independent", "venue_type": "seaside_prize", "region": "North West", "town": "Blackpool", "postcode": "FY1 5BB", "lat": 53.8150, "lon": -3.0548, "rating": 4.2, "rating_count": 430, "icp_signal": "low"},
]


def get_bingo_halls_df() -> pd.DataFrame:
    """
    Materialise the embedded snapshot as a DataFrame with derived columns
    (scope §6): rating_label, colour (RGB list for pydeck), radius_m
    (footfall proxy — scales with review count).
    """
    df = pd.DataFrame(BINGO_HALLS)
    df["rating_label"] = df.apply(
        lambda r: f"{r['rating']:.1f}★ ({int(r['rating_count'])} reviews)", axis=1
    )
    df["colour"] = df["icp_signal"].map(SIGNAL_COLOUR)
    # Radius in metres: floor + sqrt(reviews) so big halls read larger without
    # tiny venues vanishing; clipped so the map stays legible at cluster zoom.
    df["radius_m"] = (150 + df["rating_count"].pow(0.5) * 22).clip(150, 1600).round(0)
    df["signal_label"] = df["icp_signal"].map(SIGNAL_LABEL)
    return df


def _summary_metrics(df: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Venues", f"{len(df)}")
    c2.metric("Chains", f"{int((df['venue_type'] == 'chain').sum())}")
    avg = df["rating"].mean() if len(df) else 0.0
    c3.metric("Avg rating", f"{avg:.1f}★" if len(df) else "—")
    c4.metric("Total reviews", f"{int(df['rating_count'].sum()):,}")


def _render_pydeck(df: pd.DataFrame) -> bool:
    """Try the pydeck scatter map. Returns False if pydeck is unavailable."""
    try:
        import pydeck as pdk
    except Exception:
        return False

    mid_lat = float(df["lat"].mean())
    mid_lon = float(df["lon"].mean())
    # Zoom out a little when both clusters are shown, in tighter for one region.
    spread = float(df["lat"].max() - df["lat"].min()) if len(df) > 1 else 0.0
    zoom = 6.2 if spread > 0.6 else 8.5

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[lon, lat]",
        get_fill_color="colour",
        get_radius="radius_m",
        radius_min_pixels=4,
        radius_max_pixels=40,
        pickable=True,
        opacity=0.8,
        stroked=True,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
    )
    tooltip = {
        "html": (
            "<b>{name}</b><br/>"
            "{operator} · {town} {postcode}<br/>"
            "{rating_label}<br/>"
            "ICP: {signal_label}"
        ),
        "style": {"backgroundColor": "#1F1A14", "color": "white"},
    }
    st.pydeck_chart(
        pdk.Deck(
            map_style=None,  # avoids needing a Mapbox token
            initial_view_state=pdk.ViewState(
                latitude=mid_lat, longitude=mid_lon, zoom=zoom, pitch=0
            ),
            layers=[layer],
            tooltip=tooltip,
        )
    )
    return True


def render_bingo_map(key_prefix: str = "bingo") -> None:
    """
    Render the full Bingo Audience Map section: filters, summary metrics, the
    pydeck map (with st.map fallback), a venue table and a CSV export of the
    filtered set. All widget keys are namespaced with ``key_prefix`` so the
    module cannot collide with the host EDA's widgets (scope §5, §9).
    """
    df = get_bingo_halls_df()

    st.markdown(
        '<div class="page-banner"><h1>🎯 Bingo-Hall Audience Map</h1>'
        "<p>Commercial bingo venues as an audience proxy across the West Midlands "
        "and North West launch clusters. Marker size = review count (footfall "
        "proxy); colour = ICP signal.</p></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Point-in-time snapshot (Google Places, June 2026). Operators, towns and "
        "postcodes are real; coordinates are venue/locality level and ratings are "
        "representative — replace `BINGO_HALLS` with the live export for exact data."
    )

    # ---- Filters (namespaced keys) ----
    f1, f2, f3 = st.columns(3)
    regions = sorted(df["region"].unique().tolist())
    operators = sorted(df["operator"].unique().tolist())
    signals = [s for s in ["high", "low", "exclude"] if s in df["icp_signal"].unique()]

    sel_regions = f1.multiselect(
        "Region", regions, default=regions, key=f"{key_prefix}_region"
    )
    sel_operators = f2.multiselect(
        "Operator", operators, default=operators, key=f"{key_prefix}_operator"
    )
    sel_signals = f3.multiselect(
        "ICP signal",
        signals,
        default=signals,
        format_func=lambda s: SIGNAL_LABEL.get(s, s),
        key=f"{key_prefix}_signal",
    )

    fdf = df[
        df["region"].isin(sel_regions)
        & df["operator"].isin(sel_operators)
        & df["icp_signal"].isin(sel_signals)
    ].reset_index(drop=True)

    _summary_metrics(fdf)

    if fdf.empty:
        st.info("No venues match the current filters.")
        return

    # ---- Map (pydeck, with graceful fallback) ----
    if not _render_pydeck(fdf):
        st.info("pydeck unavailable — showing a basic point map.")
        st.map(fdf[["lat", "lon"]])

    # Colour legend
    st.markdown(
        "<div style='font-size:0.85rem;'>"
        "<span style='color:#1F1A14'>●</span> High (chain/club) &nbsp; "
        "<span style='color:#B89329'>●</span> Low (event/seaside) &nbsp; "
        "<span style='color:#969696'>●</span> Exclude (unverified)"
        "</div>",
        unsafe_allow_html=True,
    )

    # ---- Venue table ----
    with st.expander(f"📋 Venue table ({len(fdf)} venues)", expanded=False):
        st.dataframe(
            fdf[
                [
                    "name", "operator", "venue_type", "region", "town",
                    "postcode", "rating", "rating_count", "icp_signal",
                ]
            ],
            hide_index=True,
            use_container_width=True,
        )

    # ---- CSV export of the filtered set ----
    export = fdf.drop(columns=["colour"])
    st.download_button(
        "⬇️ Download filtered venues (CSV)",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name="bingo_halls_filtered.csv",
        mime="text/csv",
        key=f"{key_prefix}_csv",
    )


# Standalone preview:  streamlit run bingo_halls_map.py   (scope §9)
if __name__ == "__main__":
    st.set_page_config(page_title="Bingo Audience Map", layout="wide")
    render_bingo_map()
