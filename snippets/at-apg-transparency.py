# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Austrian wind output for one day from APG's transparency API (actual generation per type).

APG gives MW per quarter hour for the APG control area, each row stamped with the "Time from"
and "Time to" of its quarter hour in Austrian local time (CET/CEST). The sample is 27 October
2024, the autumn clock change, so the day has 100 quarter hours.

Traps handled:
- On the autumn change day the repeated hour is written "2A" (summer time, UTC+02:00) and "2B"
  (winter time, UTC+01:00), which date parsers reject; both are mapped to 02 with the right
  offset before converting to UTC.
- The "settlement" columns came back empty (N/A), so the "newest value" column is used.
- Recent wind values are projections from weather data until the 28th of the following month;
  this sample is long past that. The API refuses dates before 2023 (older years are in a ZIP).
"""

import io

import pandas as pd
import requests

URL = ("https://transparency.apg.at/api/v1/AGPT/Download/English/PT15M/"
       "2024-10-27T000000/2024-10-28T000000")  # must start and end at local midnight

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.content.decode("utf-8-sig").lstrip("﻿")))

start = rows["Time from [CET/CEST]"]
summer = start.str.contains(" 2A:")  # the first 02:00-03:00, still on summer time
local = pd.to_datetime(start.str.replace(r" 2[AB]:", " 02:", regex=True))
time_utc = local.dt.tz_localize("Europe/Vienna", ambiguous=summer.to_numpy()).dt.tz_convert("UTC")

df = (
    rows.assign(time_utc=time_utc)
    .set_index("time_utc")
    .sort_index()[["Wind Onshore [MW] (newest value)"]]
    .rename(columns={"Wind Onshore [MW] (newest value)": "wind_mw"})
)
assert df.index.is_unique and len(df) == 100  # 25 local hours on the autumn change day
print(df)
print(f"{len(df)} quarter hours, {df['wind_mw'].sum() * 0.25 / 1000:.1f} GWh")  # MW x 0.25 h
