# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Monthly wind generation by country from Ember's global monthly electricity data (no key).

One CSV (about 4.5 MB) with a row per area, month and source, in the layout used since July
2026: "Date" is the first day of the month and "Generation (TWh)" the energy in it. Traps handled:
- regional aggregates (World, EU, ASEAN and so on) sit in the same file; only "Area type" =
  "Country or economy" is kept;
- months are labelled by their first day, so they are turned into a "YYYY-MM" period label;
- Kosovo has Ember's own code XKX, not an ISO code, so the area name is kept beside it.
The global file has one Wind source with no onshore/offshore split, and countries start and end
in different months (most of Europe from January 2015). European months are mostly net
ENTSO-E figures, unlike Ember's gross yearly file.
"""

import io

import pandas as pd
import requests

URL = ("https://files.ember-energy.org/public-downloads/generation/outputs/"
       "release_generation_monthly_global.csv")

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.text))
rows = rows[(rows["Area type"] == "Country or economy") & (rows["Electricity source"] == "Wind")]

df = (
    rows.assign(period=pd.to_datetime(rows["Date"]).dt.strftime("%Y-%m"))
    .rename(columns={"Area": "area", "ISO 3 code": "iso3", "Generation (TWh)": "wind_twh"})
    .set_index("period")
    .sort_index()[["area", "iso3", "wind_twh"]]
)
print(df)
y2025 = df[df.index.str.startswith("2025")]
print(f"{len(df)} country-months, {df['area'].nunique()} countries; "
      f"2025: {y2025['wind_twh'].sum():.0f} TWh over {y2025['area'].nunique()} countries")
