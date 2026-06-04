"""
Generate realistic synthetic demographic data for demonstration.
Based on ONS Census 2021 statistics for England & Wales.
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Known statistics from Census 2021
UK_FEMALE_PCT = 50.6  # 50.6% female population
LONE_PARENT_PCT = 10.4  # 10.4% lone parent households
SINGLE_ADULT_PCT = 18.5  # 18.5% single adult households

# Top 50 LAs by population (approximate)
TOP_LAS = [
    ("E09000001", "City of London", 8771),
    ("E09000002", "Barking and Dagenham", 211139),
    ("E09000003", "Barnet", 389101),
    ("E09000004", "Bexley", 246369),
    ("E09000005", "Brent", 340027),
    ("E09000006", "Bromley", 329281),
    ("E09000007", "Camden", 210136),
    ("E09000008", "Croydon", 391162),
    ("E09000009", "Ealing", 367025),
    ("E09000010", "Enfield", 329383),
    ("E09000011", "Greenwich", 291080),
    ("E09000012", "Hackney", 259146),
    ("E09000013", "Hammersmith and Fulham", 183545),
    ("E09000014", "Haringey", 258588),
    ("E09000015", "Harrow", 261208),
    ("E09000016", "Havering", 259552),
    ("E09000017", "Hillingdon", 305700),
    ("E09000018", "Hounslow", 289298),
    ("E09000019", "Islington", 216871),
    ("E09000020", "Kensington and Chelsea", 143384),
    ("E09000021", "Kingston upon Thames", 169352),
    ("E09000022", "Lambeth", 317651),
    ("E09000023", "Lewisham", 300893),
    ("E09000024", "Merton", 215144),
    ("E09000025", "Newham", 352005),
    ("E09000026", "Redbridge", 310911),
    ("E09000027", "Richmond upon Thames", 195277),
    ("E09000028", "Southwark", 307650),
    ("E09000029", "Sutton", 209639),
    ("E09000030", "Tower Hamlets", 310506),
    ("E09000031", "Waltham Forest", 278428),
    ("E09000032", "Wandsworth", 329677),
    ("E09000033", "Westminster", 204300),
    ("E08000001", "Bolton", 296366),
    ("E08000002", "Bury", 193606),
    ("E08000003", "Manchester", 552858),
    ("E08000004", "Oldham", 237627),
    ("E08000005", "Rochdale", 223941),
    ("E08000006", "Salford", 261582),
    ("E08000007", "Stockport", 295829),
    ("E08000008", "Tameside", 227852),
    ("E08000009", "Trafford", 235493),
    ("E08000010", "Wigan", 330714),
    ("E08000011", "Knowsley", 152506),
    ("E08000012", "Liverpool", 486100),
    ("E08000013", "St. Helens", 183388),
    ("E08000014", "Sefton", 274707),
    ("E08000015", "Wirral", 320914),
    ("E08000016", "Barnsley", 248981),
    ("E08000017", "Doncaster", 308754),
    ("E08000018", "Rotherham", 265043),
    ("E08000019", "Sheffield", 556521),
]

def generate_sex_data():
    """Generate sex by LA data."""
    rows = []
    for la_code, la_name, total in TOP_LAS:
        female = int(total * UK_FEMALE_PCT / 100)
        male = total - female
        rows.append({
            "la_code": la_code,
            "la_name": la_name,
            "female": female,
            "male": male,
            "total": total,
            "female_pct": round(UK_FEMALE_PCT, 1),
        })
    return pd.DataFrame(rows)

def generate_household_data():
    """Generate household composition by LA data."""
    np.random.seed(42)
    rows = []
    for la_code, la_name, population in TOP_LAS:
        # Approximate 2.4 people per household
        households = int(population / 2.4)
        rows.append({
            "la_code": la_code,
            "la_name": la_name,
            "total_households": households,
            "lone_parent_pct": round(LONE_PARENT_PCT + np.random.normal(0, 1), 1),
            "single_adult_pct": round(SINGLE_ADULT_PCT + np.random.normal(0, 1.5), 1),
        })
    return pd.DataFrame(rows)

def generate_venue_data():
    """Generate gambling venue data by LA."""
    np.random.seed(42)
    rows = []
    for la_code, la_name, population in TOP_LAS:
        # Scale venues by population density (rough estimate)
        # Urban areas have more venues per capita
        bingo = max(0, int(np.random.poisson(population / 50000)))
        casinos = max(0, int(np.random.poisson(population / 200000)))
        betting = max(1, int(np.random.poisson(population / 8000)))
        arcades = max(0, int(np.random.poisson(population / 30000)))
        rows.append({
            "la_code": la_code,
            "la_name": la_name,
            "bingo_halls": bingo,
            "casinos": casinos,
            "betting_shops": betting,
            "arcades": arcades,
            "total_venues": bingo + casinos + betting + arcades,
        })
    return pd.DataFrame(rows)

def generate_companies_data():
    """Generate leisure/gambling company data by LA."""
    np.random.seed(42)
    rows = []
    for la_code, la_name, population in TOP_LAS:
        # Companies scale with population and urban density
        gambling = max(0, int(np.random.poisson(population / 40000)))
        leisure = max(1, int(np.random.poisson(population / 15000)))
        rows.append({
            "la_code": la_code,
            "la_name": la_name,
            "gambling_companies": gambling,
            "leisure_companies": leisure,
            "total_companies": gambling + leisure,
        })
    return pd.DataFrame(rows)

if __name__ == "__main__":
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating demo data...")
    
    sex_df = generate_sex_data()
    sex_df.to_csv(output_dir / "10_sex_by_la.csv", index=False)
    print(f"✅ 10_sex_by_la.csv: {len(sex_df)} LAs")
    
    hh_df = generate_household_data()
    hh_df.to_csv(output_dir / "11_household_composition_la.csv", index=False)
    print(f"✅ 11_household_composition_la.csv: {len(hh_df)} LAs")
    
    venue_df = generate_venue_data()
    venue_df.to_csv(output_dir / "13_gambling_venues_by_la.csv", index=False)
    print(f"✅ 13_gambling_venues_by_la.csv: {len(venue_df)} LAs")
    
    comp_df = generate_companies_data()
    comp_df.to_csv(output_dir / "14_leisure_companies_by_la.csv", index=False)
    print(f"✅ 14_leisure_companies_by_la.csv: {len(comp_df)} LAs")
    
    print("\nDemo data generated successfully!")
    print("Note: This is synthetic data for demonstration purposes.")
    print("Real data requires Nomis API access for Census and bulk downloads for GC/CH data.")
