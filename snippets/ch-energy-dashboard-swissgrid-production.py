# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Daily Swiss wind production for one year, from the Energy Dashboard's Swissgrid dataset.

The dashboard's public API serves the ogd104 table: one value per day and energy carrier, in
GWh. Traps handled:
- the table holds rows up to about 11 days in the future, evidently projections, so every row
  dated today or later is dropped;
- the API returns at most 1,000 rows a call, so one year of wind is asked for at a time;
- the parameter is "filters": a misspelt one is ignored and every carrier comes back, so the
  carrier column is checked.
Which time zone defines the day is not documented, so df keeps the date label as "period"
rather than inventing UTC times. Values are rounded to 0.1 GWh, which is coarse on calm days,
and past values are revised without notice: record the download date.
"""

import pandas as pd
import requests

YEAR = 2025

resp = requests.get(
    "https://energiedashboard.ch/api/v1/datasets/stromproduktion-swissgrid/data",
    params={"filters": "energietraeger===Wind", "from": f"{YEAR}-01-01T00:00:00.000Z",
            "to": f"{YEAR}-12-31T00:00:00.000Z", "limit": 1000},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["data"])
assert set(rows["energietraeger"]) == {"Wind"}  # the filter was applied

today = pd.Timestamp.now(tz="Europe/Zurich").strftime("%Y-%m-%d")
df = (
    rows[rows["datum"] < today]
    .rename(columns={"datum": "period", "produktion_gwh": "wind_gwh"})
    .set_index("period")
    .sort_index()[["wind_gwh"]]
)
print(df)
print(f"{len(df)} days, {df['wind_gwh'].sum():.1f} GWh")
