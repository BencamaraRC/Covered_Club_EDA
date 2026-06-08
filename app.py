"""
Covered Club UK Market Analysis Dashboard

Streamlit app for visualizing CLPI rankings, prize-vs-spend ratios,
and affordability analysis for the Covered Club UK market analysis.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from src.agent.executor import run_agent

# Page configuration
st.set_page_config(
    page_title="Covered Club UK Market Analysis",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Data loading functions
@st.cache_data
def load_clpi_data():
    """Load CLPI composite data."""
    path = Path("data/output/09_clpi_composite.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_quintile_data():
    """Load quintile spending data."""
    path = Path("data/output/04_quintile_spend.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_prize_data():
    """Load prize vs affordability data."""
    path = Path("data/output/08_prize_vs_affordability.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_gambling_data():
    """Load gambling market data."""
    path = Path("data/output/07_gambling_market.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_gdhi_data():
    """Load GDHI regional data."""
    path = Path("data/output/06_gdhi_region.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_census_data():
    """Load Census population data."""
    path = Path("data/raw/census_population_lsoa.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_sex_data():
    """Load Census sex by LA data."""
    path = Path("data/output/10_sex_by_la.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_household_data():
    """Load household composition by LA data."""
    path = Path("data/output/11_household_composition_la.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_uc_data():
    """Load Universal Credit claimants by sex and LA."""
    path = Path("data/output/12_uc_claimants_by_sex_la.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_venues_data():
    """Load Gambling Commission premises by LA."""
    path = Path("data/output/13_gambling_venues_by_la.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_companies_data():
    """Load Companies House leisure/gambling companies by LA."""
    path = Path("data/output/14_leisure_companies_by_la.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_gambling_spend_data():
    """Load gambling spend by region."""
    path = Path("data/output/15_gambling_spend_by_region.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


# Load data
clpi_df = load_clpi_data()
quintile_df = load_quintile_data()
prize_df = load_prize_data()
gambling_df = load_gambling_data()
gdhi_df = load_gdhi_data()
census_df = load_census_data()
sex_df = load_sex_data()
household_df = load_household_data()
uc_df = load_uc_data()
venues_df = load_venues_data()
companies_df = load_companies_data()
gambling_spend_df = load_gambling_spend_data()

# Sidebar
st.sidebar.title("Covered Club Dashboard")
st.sidebar.markdown("---")

# Page selection
page = st.sidebar.radio(
    "Select Analysis",
    [
        "Where to Launch (CLPI Rankings)",
        "Target Areas Map",
        "Which Prize to Lead With",
        "What to Charge (Affordability)",
        "Market Overview",
        "Ask the Analyst (AI)",
    ],
)

# CLPI Weight Controls — live, recomputes rankings on change
st.sidebar.markdown("### CLPI Weights")
st.sidebar.caption("Drag to reweight the index — rankings update instantly.")

w_dep_pct = st.sidebar.slider("Deprivation", 0, 100, 50, step=5, format="%d%%")
w_fp_pct = st.sidebar.slider("Fuel poverty", 0, 100, 25, step=5, format="%d%%")
w_inc_pct = st.sidebar.slider("Income gap", 0, 100, 25, step=5, format="%d%%")

_wtotal = w_dep_pct + w_fp_pct + w_inc_pct
if _wtotal == 0:
    st.sidebar.warning("Weights can't all be 0 — reverting to default 50/25/25.")
    w_dep_pct, w_fp_pct, w_inc_pct, _wtotal = 50, 25, 25, 100

# Normalise so the three weights always sum to 100%, whatever the sliders total
wn_dep = w_dep_pct / _wtotal
wn_fp = w_fp_pct / _wtotal
wn_inc = w_inc_pct / _wtotal
if _wtotal != 100:
    st.sidebar.caption(
        f"Normalised to **{wn_dep:.0%}** deprivation · "
        f"**{wn_fp:.0%}** fuel · **{wn_inc:.0%}** income"
    )

# Recompute CLPI live from the component scores already in the dataset
# (same formula as src/analyse/clpi.py — no pipeline re-run needed).
if not clpi_df.empty:
    clpi_df = clpi_df.copy()
    clpi_df["clpi_score"] = (
        wn_dep * clpi_df["score_deprivation"]
        + wn_fp * clpi_df["score_fuel_poverty"]
        + wn_inc * clpi_df["score_income_gap"]
    ).round(1)
    clpi_df = clpi_df.sort_values("clpi_score", ascending=False).reset_index(
        drop=True
    )
    clpi_df["clpi_rank"] = clpi_df.index + 1

st.sidebar.markdown("---")
st.sidebar.markdown("### Data Sources")
st.sidebar.markdown("- MHCLG Indices of Deprivation 2025")
st.sidebar.markdown("- DESNZ Fuel Poverty 2026")
st.sidebar.markdown("- ONS Regional GDHI 2023")
st.sidebar.markdown("- ONS Family Spending FYE 2024")

# Main content
if page == "Where to Launch (CLPI Rankings)":
    st.markdown(
        '<h1 class="main-header">Where to Launch: CLPI Rankings</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "The Cost-of-Living Pressure Index (CLPI) identifies areas with the highest cost-of-living pressure, making them prime target markets for Covered Club."
    )

    if clpi_df.empty:
        st.error("CLPI data not found. Please ensure the pipeline has been run.")
    else:
        # Top 20 CLPI rankings
        st.markdown("### Top 20 Local Authorities by CLPI Score")

        col1, col2 = st.columns([2, 1])

        with col1:
            # Bar chart of top 20
            top20 = clpi_df.head(20)
            fig = px.bar(
                top20,
                x="clpi_score",
                y="la_name",
                orientation="h",
                title="Top 20 Local Authorities by CLPI Score",
                color="clpi_score",
                color_continuous_scale="Reds",
                labels={"clpi_score": "CLPI Score", "la_name": "Local Authority"},
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Key metrics
            st.markdown("### Key Insights")
            top_la = clpi_df.iloc[0]
            st.metric("Top Target Area", top_la["la_name"])

            with st.expander("ℹ️ What is CLPI Score?"):
                st.markdown(
                    f"""
                **CLPI (Cost-of-Living Pressure Index)** measures overall economic pressure in an area (0-100 scale).

                **Formula**: {wn_dep:.0%} × Deprivation + {wn_fp:.0%} × Fuel Poverty + {wn_inc:.0%} × Income Gap

                Higher scores = more pressure = better target market for Covered Club.
                """
                )
            st.metric("CLPI Score", f"{top_la['clpi_score']:.1f}")

            with st.expander("ℹ️ What is IMD Rank?"):
                st.markdown(
                    """
                **IMD (Index of Multiple Deprivation)** is the official UK government measure of relative deprivation.
                
                Rank #1 = most deprived area in England (out of 296 local authorities).
                
                Combines 7 domains: income, employment, education, health, crime, housing, living environment.
                """
                )
            st.metric("IMD Rank", f"#{top_la['imd_2025_avg_score_rank']}")

            with st.expander("ℹ️ What is Fuel Poverty?"):
                st.markdown(
                    """
                **Fuel Poverty** = % of households unable to afford adequate heating.
                
                A household is in fuel poverty if required fuel costs are above median level AND 
                residual income after paying fuel is below the poverty line.
                
                England average: 9.9%
                """
                )
            st.metric("Fuel Poverty", f"{top_la['fuel_poverty_pct_2024']:.1f}%")

            with st.expander("📊 CLPI Components Explained"):
                st.markdown(
                    f"""
                **Deprivation Score ({top_la['score_deprivation']:.1f})**: Normalized from IMD rank (0-100).
                Formula: (296 − IMD Rank) ÷ 296 × 100
                
                **Fuel Poverty Score ({top_la['score_fuel_poverty']:.1f})**: Normalized vs England's worst rate (0-100).
                Formula: (LA Rate ÷ Max Rate) × 100
                
                **Income Gap Score ({top_la['score_income_gap']:.1f})**: Gap between regional and UK average income (0-100).
                Formula: (UK Avg GDHI − Region GDHI) ÷ UK Avg GDHI × 100
                
                **Weights**: {wn_dep:.0%} deprivation / {wn_fp:.0%} fuel poverty / {wn_inc:.0%} income gap
                """
                )

        st.markdown("---")

        # Full data table with filters
        st.markdown("### Full CLPI Rankings")

        # Region filter
        regions = ["All"] + sorted(clpi_df["region"].unique().tolist())
        selected_region = st.selectbox("Filter by Region", regions)

        if selected_region != "All":
            filtered_df = clpi_df[clpi_df["region"] == selected_region]
        else:
            filtered_df = clpi_df

        st.dataframe(
            filtered_df[
                [
                    "clpi_rank",
                    "la_name",
                    "region",
                    "clpi_score",
                    "score_deprivation",
                    "score_fuel_poverty",
                    "score_income_gap",
                    "imd_2025_avg_score_rank",
                    "fuel_poverty_pct_2024",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

elif page == "Target Areas Map":
    st.markdown('<h1 class="main-header">Target Areas Map</h1>', unsafe_allow_html=True)
    st.markdown(
        "Interactive map showing CLPI scores by local authority. Click on areas to view detailed demographics."
    )

    with st.expander("ℹ️ About This Map"):
        st.markdown(
            """
        **Current Version**: Local Authority (LA) level view
        
        This map shows CLPI scores shaded by intensity:
        - **Red/Dark**: High pressure areas (best target markets)
        - **Blue/Light**: Low pressure areas (lower priority)
        
        **Future Enhancement**: Will be upgraded to postcode district level for more granular targeting.
        
        **Data Sources**: MHCLG IMD 2025, DESNZ Fuel Poverty 2026, ONS GDHI 2023
        """
        )

    if clpi_df.empty:
        st.error("CLPI data not found. Please ensure the pipeline has been run.")
    else:
        # Map visualization using Plotly choropleth
        # Note: Full UK LA boundaries require GeoJSON file
        # For now, showing a bar chart as a proxy that will be upgraded to map

        st.markdown("### Top 20 Target Areas by CLPI Score")

        fig = px.bar(
            clpi_df.head(20),
            x="clpi_score",
            y="la_name",
            color="clpi_score",
            color_continuous_scale="RdYlGn_r",  # Red (high) to Green (low)
            orientation="h",
            title="Top 20 Local Authorities by CLPI Score",
            labels={"clpi_score": "CLPI Score", "la_name": "Local Authority"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### Select an Area for Detailed Analysis")

        # Area selector
        selected_la = st.selectbox(
            "Select Local Authority",
            options=clpi_df["la_name"].tolist(),
            index=0,
        )

        # Display selected area details
        la_data = clpi_df[clpi_df["la_name"] == selected_la].iloc[0]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("CLPI Score", f"{la_data['clpi_score']:.1f}")
            st.metric("CLPI Rank", f"#{la_data['clpi_rank']}")

        with col2:
            st.metric("IMD Rank", f"#{la_data['imd_2025_avg_score_rank']}")
            st.metric("Fuel Poverty", f"{la_data['fuel_poverty_pct_2024']:.1f}%")

        with col3:
            st.metric("Deprivation Score", f"{la_data['score_deprivation']:.1f}")
            st.metric("Income Gap Score", f"{la_data['score_income_gap']:.1f}")

        st.markdown("---")
        st.markdown(f"### Demographic Profile — {selected_la}")

        # Look up the selected LA in each demographic dataset (keyed by la_name).
        uc_row = uc_df[uc_df["la_name"] == selected_la] if not uc_df.empty else uc_df
        hh_row = (
            household_df[household_df["la_name"] == selected_la]
            if not household_df.empty
            else household_df
        )
        sex_row = sex_df[sex_df["la_name"] == selected_la] if not sex_df.empty else sex_df

        if uc_row.empty and hh_row.empty and sex_row.empty:
            st.info(f"No demographic data available for {selected_la} yet.")
        else:
            d1, d2, d3 = st.columns(3)

            with d1:
                st.markdown("**Universal Credit** · *DWP*")
                if not uc_row.empty:
                    r = uc_row.iloc[0]
                    st.metric("UC claimants", f"{int(r['total_claimants']):,}")
                    st.metric("Female claimants", f"{r['female_claimant_pct']:.0f}%")
                else:
                    st.caption("Not available for this area.")

            with d2:
                st.markdown("**Households** · *Census 2021*")
                if not hh_row.empty:
                    r = hh_row.iloc[0]
                    st.metric("Households", f"{int(r['total_households']):,}")
                    st.metric("Lone-parent", f"{r['lone_parent_pct']:.1f}%")
                    st.metric("Single-adult", f"{r['single_adult_pct']:.1f}%")
                else:
                    st.caption("Not available for this area.")

            with d3:
                st.markdown("**Population** · *Census 2021*")
                if not sex_row.empty:
                    r = sex_row.iloc[0]
                    st.metric("Residents", f"{int(r['total']):,}")
                    st.metric("Female", f"{r['female_pct']:.1f}%")
                else:
                    st.caption("Not available for this area.")

            st.caption(
                "ℹ️ Universal Credit counts are live DWP figures (cover almost every "
                "authority). Census population & household figures are currently "
                "demo-populated for a subset of areas — run "
                "`python -m src.ingest.census` with a NOMIS API key for full national "
                "coverage."
            )

        st.markdown("---")
        st.markdown("### Recommended Prize for This Area")

        # Simple recommendation based on fuel poverty
        if la_data["fuel_poverty_pct_2024"] > 12:
            st.success(
                f"**Recommendation**: Lead with **Heating Help** or **Fuel Covered** prizes - high fuel poverty ({la_data['fuel_poverty_pct_2024']:.1f}%) indicates strong bill-paying pain point"
            )
        elif la_data["score_deprivation"] > 90:
            st.success(
                f"**Recommendation**: Lead with **Food Shop Friday** - high deprivation score ({la_data['score_deprivation']:.1f}) suggests food cost pressure"
            )
        else:
            st.info("All prizes are viable - consider A/B testing different offers")

elif page == "Which Prize to Lead With":
    st.markdown(
        '<h1 class="main-header">Which Prize to Lead With</h1>', unsafe_allow_html=True
    )
    st.markdown(
        "Prize-vs-spend ratios help prioritize which prize should lead acquisition campaigns. Higher ratios indicate stronger value framing."
    )

    with st.expander("ℹ️ How is this calculated?"):
        st.markdown(
            """
        **Prize vs Annual Spend Ratio** = Prize Amount ÷ (Weekly Category Spend × 52) × 100
        
        This shows how much the prize is worth relative to what UK households spend annually on that category.
        
        Example: If a prize is worth 200% of annual spend, it means the prize covers 2 years of typical spending.
        
        Higher ratios = stronger value proposition for customers.
        """
        )

    if prize_df.empty:
        st.error("Prize data not found. Please ensure the pipeline has been run.")
    else:
        # Filter out incomplete rows (Childcare has missing data)
        complete_prizes = prize_df[prize_df["annual_category_spend_£"].notna()].copy()

        # Bar chart
        fig = px.bar(
            complete_prizes,
            x="competition",
            y="prize_as_pct_of_annual_spend",
            title="Prize Value as % of Annual Category Spend",
            color="prize_as_pct_of_annual_spend",
            color_continuous_scale="Blues",
            labels={
                "prize_as_pct_of_annual_spend": "Prize as % of Annual Spend",
                "competition": "Competition",
            },
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # Detailed table
        st.markdown("### Detailed Prize Analysis")

        col1, col2, col3 = st.columns(3)

        for idx, row in complete_prizes.iterrows():
            with col1:
                st.markdown(f"**{row['competition']}**")
                st.metric("Ticket Price", f"£{row['ticket_£']}")
                st.metric("Prize Value", f"£{row['prize_£']}")

            with col2:
                st.metric("Weekly Pain Point", f"£{row['weekly_pain_£']}")
                st.metric(
                    "Annual Category Spend", f"£{row['annual_category_spend_£']:.0f}"
                )

            with col3:
                ratio = row["prize_as_pct_of_annual_spend"]
                st.metric("Prize vs Annual Spend", f"{ratio:.0f}%")
                st.markdown(f"*Prize is {ratio/100:.1f}× annual spend*")

            st.markdown("---")

        # Recommendation
        best_prize = complete_prizes.loc[
            complete_prizes["prize_as_pct_of_annual_spend"].idxmax()
        ]
        st.success(
            f"**Recommendation:** Lead with **{best_prize['competition']}** - highest value framing at {best_prize['prize_as_pct_of_annual_spend']:.0f}% of annual spend"
        )

elif page == "What to Charge (Affordability)":
    st.markdown(
        '<h1 class="main-header">What to Charge: Affordability Analysis</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "Affordability analysis evaluates ticket prices as a percentage of non-essential weekly spend by income quintile. This answers 'can customers afford tickets without sacrificing essentials?'"
    )

    with st.expander("ℹ️ What is Non-Essential Spend?"):
        st.markdown(
            """
        **Non-Essential Weekly Spend** = Total Weekly Spend × (1 − Essentials %)
        
        **Essentials %** = Housing/Fuel/Power share + Food share
        
        This represents the discretionary income available after covering basic needs.
        
        The analysis evaluates whether a ticket price is reasonable relative to this discretionary income.
        """
        )

    if quintile_df.empty:
        st.error("Quintile data not found. Please ensure the pipeline has been run.")
    else:
        # Ticket price slider
        st.markdown("### Adjust Ticket Price")
        ticket_price = st.slider("Ticket Price (£)", 5, 25, 10, 1)
        st.info(
            "💡 Use the slider to see how different ticket prices affect affordability across income quintiles."
        )

        # Calculate affordability for selected price
        quintile_df["affordable_tickets_weekly"] = (
            quintile_df["non_essential_weekly_£"] / ticket_price
        ).round(1)
        quintile_df["ticket_as_pct_of_non_essential"] = (
            ticket_price / quintile_df["non_essential_weekly_£"] * 100
        ).round(1)

        # Chart
        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                name="Non-Essential Weekly Spend",
                x=quintile_df["quintile"],
                y=quintile_df["non_essential_weekly_£"],
                marker_color="lightblue",
            )
        )

        fig.add_trace(
            go.Bar(
                name=f"Ticket Price (£{ticket_price})",
                x=quintile_df["quintile"],
                y=[ticket_price] * len(quintile_df),
                marker_color="red",
            )
        )

        fig.update_layout(
            title=f"Non-Essential Weekly Spend vs Ticket Price (£{ticket_price})",
            barmode="group",
            xaxis_title="Income Quintile",
            yaxis_title="£ per Week",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Affordability table
        st.markdown("### Affordability by Quintile")

        for idx, row in quintile_df.iterrows():
            pct = row["ticket_as_pct_of_non_essential"]
            tickets = row["affordable_tickets_weekly"]

            # Color coding for affordability
            if pct <= 5:
                status = "✅ Highly Affordable"
                color = "green"
            elif pct <= 10:
                status = "⚠️ Moderate"
                color = "orange"
            else:
                status = "❌ Less Affordable"
                color = "red"

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"**{row['quintile']}**")
            with col2:
                st.metric(
                    f"Non-Essential Spend", f"£{row['non_essential_weekly_£']:.2f}"
                )
            with col3:
                st.metric(f"£{ticket_price} as % of Non-Essential", f"{pct}%")
            with col4:
                st.markdown(
                    f"<span style='color:{color}'>{status}</span>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.markdown("### Responsible Gambling Threshold")

        with st.expander("ℹ️ What is the Responsible Gambling Threshold?"):
            st.markdown(
                """
            **Industry Guidance**: Tickets should not exceed 5% of non-essential discretionary income.
            
            This threshold helps ensure that gambling/prize draw participation doesn't compromise essential spending.
            
            **Color Coding**:
            - ✅ Green (≤5%): Highly Affordable
            - ⚠️ Orange (5-10%): Moderate
            - ❌ Red (>10%): Less Affordable
            
            At £10 ticket price, the threshold is met for Q1 (poorest) through Q4.
            """
            )

        st.info(
            "Industry guidance suggests tickets should not exceed 5% of non-essential discretionary income. At £10, this threshold is met for Q1 (poorest) through Q4."
        )

elif page == "Market Overview":
    st.markdown('<h1 class="main-header">Market Overview</h1>', unsafe_allow_html=True)
    st.markdown("Key market statistics for the UK prize draw and gambling market.")

    if not gambling_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Prize Draw Market")

            with st.expander("ℹ️ About PDC Market"):
                st.markdown(
                    """
                **PDC (Prize Draws & Competitions)**: Free-to-enter prize draws and competitions.
                
                **Source**: DCMS / London Economics PDC Study 2025
                
                **Key Insight**: 88% of PDC participants also gamble or play lottery (vs 60% in wider population), showing strong crossover with gambling behavior.
                """
                )

            pdc_participants = gambling_df[
                gambling_df["metric"]
                == "UK adults in prize draws/competitions (PDC) annually"
            ]["value"].values[0]
            pdc_value = gambling_df[gambling_df["metric"] == "Annual PDC market value"][
                "value"
            ].values[0]
            overlap = gambling_df[
                gambling_df["metric"]
                == "PDC participants who also gamble or play lottery"
            ]["value"].values[0]

            st.metric("Annual PDC Participants", pdc_participants)
            st.metric("Annual Market Value", pdc_value)
            st.metric("Gambling Overlap", overlap)

        with col2:
            st.markdown("### Gambling Participation")

            with st.expander("ℹ️ About Gambling Statistics"):
                st.markdown(
                    """
                **Source**: Gambling Commission Gambling Survey for Great Britain (GSGB) 2024-25
                
                **Gambling (Last 4 Weeks)**: % of UK adults who participated in any form of gambling in the past 4 weeks.
                
                **Note**: These figures are for Great Britain only (excludes Northern Ireland).
                """
                )

            gambling_4w = gambling_df[
                gambling_df["metric"] == "UK adults gambling in last 4 weeks"
            ]["value"].values[0]
            lottery = gambling_df[
                gambling_df["metric"] == "UK adults playing National Lottery"
            ]["value"].values[0]
            scratchcards = gambling_df[
                gambling_df["metric"] == "UK adults playing scratchcards"
            ]["value"].values[0]

            st.metric("Gambling (Last 4 Weeks)", gambling_4w)
            st.metric("National Lottery", lottery)
            st.metric("Scratchcards", scratchcards)

    st.markdown("---")

    if not gdhi_df.empty:
        st.markdown("### Regional Disposable Income (GDHI)")

        with st.expander("ℹ️ What is GDHI?"):
            st.markdown(
                """
            **GDHI (Gross Disposable Household Income)**: The amount of money households have available for spending or saving after taxes and benefits.
            
            **Per Head**: Calculated by dividing total regional GDHI by population.
            
            **Source**: ONS Regional Accounts, September 2025 release (2023 data).
            
            **Why it matters**: Lower GDHI regions have less disposable income, making them better target markets for bill-paying prizes.
            """
            )

        fig = px.bar(
            gdhi_df,
            x="gdhi_per_head_£",
            y="region",
            orientation="h",
            title="Regional Gross Disposable Household Income per Head (£)",
            color="gdhi_per_head_£",
            color_continuous_scale="Viridis",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### About This Analysis")
    st.markdown(
        f"""
    This dashboard uses published UK statistics to triangulate market insights for Covered Club:

    - **Data Sources**: MHCLG, DESNZ, ONS, Gambling Commission, DCMS
    - **Geographic Unit**: Lower-layer Super Output Area (LSOA) rolled up to Local Authority
    - **CLPI Formula**: {wn_dep:.0%} deprivation + {wn_fp:.0%} fuel poverty + {wn_inc:.0%} income gap (live-weighted)
    - **Limitations**: No first-party customer data pre-launch; all figures from published statistics
    
    For detailed methodology, see `docs/analytical_approach.md`
    """
    )

elif page == "Ask the Analyst (AI)":
    st.markdown('<h1 class="main-header">Ask the Analyst</h1>', unsafe_allow_html=True)
    st.markdown(
        "Ask any business question about the Covered Club market data. "
        "The analyst can query datasets, generate charts, re-run the pipeline with custom weights, "
        "and write new persistent dashboard pages."
    )

    # Session state for chat history
    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []
    if "agent_figures" not in st.session_state:
        st.session_state.agent_figures = []

    # Sidebar context panel
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Analyst Context")
    datasets_loaded = [
        name
        for name, df in [
            ("clpi", clpi_df),
            ("quintile", quintile_df),
            ("prize", prize_df),
            ("gambling", gambling_df),
            ("gdhi", gdhi_df),
            ("sex_by_la", sex_df),
            ("household_composition", household_df),
            ("uc_claimants", uc_df),
            ("gambling_venues", venues_df),
            ("leisure_companies", companies_df),
            ("gambling_spend_by_region", gambling_spend_df),
        ]
        if not df.empty
    ]
    st.sidebar.markdown(f"**Datasets loaded:** {', '.join(datasets_loaded)}")
    if st.sidebar.button("Clear conversation"):
        st.session_state.agent_messages = []
        st.session_state.agent_figures = []
        st.rerun()

    # Example prompts
    with st.expander("💡 Example questions"):
        st.markdown(
            """
        - *Which 5 local authorities should we target first for our launch campaign?*
        - *Which prize has the strongest value framing relative to annual household spend?*
        - *At £10 a ticket, what % of Q1 households can afford to enter within the 5% responsible gambling threshold?*
        - *Reweight CLPI to 60% fuel poverty, 20% deprivation, 20% income gap — which areas move up?*
        - *Create a new dashboard page called 'North West Deep Dive' with the top 10 LAs in that region*
        - *Show me a scatter of CLPI score vs fuel poverty % coloured by region*
        """
        )

    # Chat history
    for i, msg in enumerate(st.session_state.agent_messages):
        role = msg["role"]
        if role == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
                # Render any figures associated with this message
                for fig in st.session_state.agent_figures:
                    if fig.get("message_index") == i:
                        st.plotly_chart(fig["figure"], use_container_width=True)

    # Input
    dataframes = {
        "clpi": clpi_df,
        "quintile": quintile_df,
        "prize": prize_df,
        "gambling": gambling_df,
        "gdhi": gdhi_df,
        "sex_by_la": sex_df,
        "household_composition": household_df,
        "uc_claimants": uc_df,
        "gambling_venues": venues_df,
        "leisure_companies": companies_df,
        "gambling_spend_by_region": gambling_spend_df,
    }

    if prompt := st.chat_input("Ask a question about the data..."):
        st.session_state.agent_messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                claude_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.agent_messages
                    if m["role"] in ("user", "assistant")
                ]
                answer, figures, pipeline_rerun = run_agent(claude_messages, dataframes)

            st.markdown(answer)

            message_index = len(st.session_state.agent_messages)
            for fig in figures:
                st.plotly_chart(fig, use_container_width=True)
                st.session_state.agent_figures.append(
                    {"figure": fig, "message_index": message_index}
                )

            if pipeline_rerun:
                st.success(
                    "✅ Pipeline re-run complete. Reload the page to see updated data."
                )

        st.session_state.agent_messages.append({"role": "assistant", "content": answer})


# Footer
st.markdown("---")
st.markdown(
    "*Covered Club UK Market Analysis Dashboard | Data Sources: MHCLG, DESNZ, ONS, Gambling Commission*"
)
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.8rem; margin-top:0.5rem;'>"
    "🔒 <strong>Private &amp; Confidential</strong> — Prepared for Covered Club by CamSoft Analytics. "
    "Not for distribution."
    "</div>",
    unsafe_allow_html=True,
)
