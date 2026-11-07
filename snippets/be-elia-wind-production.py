# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Belgian wind output for one day from Elia's open data (dataset ods031).

Each row is the measured-and-upscaled mean MW over a quarter hour for one slice of the fleet
(onshore or offshore, region, Elia or distribution grid), stamped at the period start in UTC,
with the capacity Elia monitors for that slice.

Traps handled:
- Rows are split by onshore/offshore, region and grid connection, so national output and
  capacity are both summed over the same rows in each quarter hour.
- The portal shows local time, but the API returns UTC ("+00:00"); the stamps are read as UTC.
- The stored load factor is a fraction (not a percentage) and can exceed 1, so it is not used;
  a national load factor is recomputed from the summed output and capacity.
"""

import io

import pandas as pd
import requests

START, END = "2024-01-15T00:00:00Z", "2024-01-16T00:00:00Z"  # one UTC day

resp = requests.get(
    "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods031/exports/csv",
    params={"where": f'datetime >= "{START}" and datetime < "{END}"', "delimiter": ";"},
    timeout=60,
)
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.content.decode("utf-8-sig")), sep=";")
rows["time_utc"] = pd.to_datetime(rows["datetime"], utc=True)

wide = rows.pivot_table(index="time_utc", columns="offshoreonshore", values="measured",
                        aggfunc="sum")
df = pd.DataFrame({
    "onshore_mw": wide["Onshore"],
    "offshore_mw": wide["Offshore"],
    "wind_mw": wide.sum(axis=1),
    "capacity_mw": rows.groupby("time_utc")["monitoredcapacity"].sum(),
}).sort_index()
df["load_factor"] = df["wind_mw"] / df["capacity_mw"]  # recomputed, a fraction
print(df)
print(f"{len(df)} quarter hours, {df['wind_mw'].sum() * 0.25 / 1000:.1f} GWh "
      f"(mean {df['wind_mw'].mean():.0f} MW of {df['capacity_mw'].mean():.0f} MW monitored)")
