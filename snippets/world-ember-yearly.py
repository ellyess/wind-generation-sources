# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual wind generation and capacity by country from Ember's yearly electricity data (no key).

One CSV (about 2 MB) with a row per area, year and source, in the layout used since July 2026:
"Generation (TWh)" and "Capacity (GW)" sit in the same row. Traps handled:
- regional aggregates (World, EU, continents) share the file; only "Area type" = "Country or
  economy" is kept, and World is used only for the check line;
- a blank capacity stays missing rather than zero; zero generation in early years mostly marks
  the years before wind was reported, not a measured zero;
- the latest year is often an Ember projection from monthly data, and it differs by country, so
  each country's last year is marked in a "latest_year" column to treat as provisional.
Figures are gross generation, unlike Ember's mostly net monthly European file.
"""

import io

import pandas as pd
import requests

URL = ("https://files.ember-energy.org/public-downloads/generation/outputs/"
       "release_generation_yearly_global.csv")

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.text))
rows = rows[rows["Electricity source"] == "Wind"]
world = rows[rows["Area"] == "World"].set_index("Year")["Generation (TWh)"]
rows = rows[rows["Area type"] == "Country or economy"]

df = (
    rows.rename(columns={"Area": "area", "ISO 3 code": "iso3", "Year": "period",
                         "Generation (TWh)": "wind_twh", "Capacity (GW)": "capacity_gw"})
    .assign(period=lambda d: d["period"].astype(str))
    .set_index("period")
    .sort_index()[["area", "iso3", "wind_twh", "capacity_gw"]]
)
df["latest_year"] = df.index == df.groupby("area")["wind_twh"].transform(
    lambda s: s.index.max())
print(df)
print(f"{len(df)} country-years, {df['area'].nunique()} countries; 2024: "
      f"{df.loc['2024', 'wind_twh'].sum():.0f} TWh summed, {world[2024]:.0f} TWh World")
