# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Wind energy per quarter hour for one day in each Finnish, Norwegian and Swedish zone, from eSett.

eSett's EXP16 production volumes are settled metered energy in MWh per period (a quarter hour
from 23 May 2023, an hour before). Traps handled:
- several zones in one request come back summed, so each zone is requested on its own;
- the values are MWh in the quarter hour, not average MW (multiply by 4 for MW);
- each row has a local CET/CEST stamp and a UTC one; only timestampUTC is used.
eSett does not say which end of the period a stamp marks, so it is kept as published (it
matches Svenska kraftnät's Mimer data read as hour starts, but neither publisher says so).
Danish zones are not requested: their production is all under "other", with no wind split.
"""

import pandas as pd
import requests

DAY, NEXT_DAY = "2026-10-01", "2026-10-02"
API = "https://api.opendata.esett.com/EXP16"

options = requests.get(f"{API}/MBAOptions", timeout=60).json()  # eSett's own zone codes
ZONES = {m["name"]: m["code"] for c in options if c["countryCode"] != "DK" for m in c["mbas"]}

frames = []
for zone, eic in ZONES.items():  # one zone per request
    resp = requests.get(
        f"{API}/Volumes",
        params={"start": f"{DAY}T00:00:00.000Z", "end": f"{NEXT_DAY}T00:00:00.000Z", "mba": eic},
        timeout=60,
    )
    resp.raise_for_status()
    frames.append(pd.DataFrame(resp.json()).assign(zone=zone))
rows = pd.concat(frames)

df = (
    rows.assign(time_utc=pd.to_datetime(rows["timestampUTC"], utc=True))
    .set_index("time_utc")
    .sort_index()
    .rename(columns={"wind": "wind_mwh"})[["zone", "wind_mwh"]]
)
print(df)
print(f"{len(df)} zone-quarter-hours, {df['wind_mwh'].sum() / 1000:.1f} GWh "
      f"(mean {df.groupby('zone')['wind_mwh'].mean().mul(4).sum():,.0f} MW across zones)")
