# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32", "openpyxl>=3.1"]
# ///
"""One month of 10-minute SCADA data from the Vestas V52 turbine at DkIT, Dundalk (Mendeley Data).

The record (doi:10.17632/tm988rs48k.2) is one 79 MB xlsx sheet, 2006 to 2020, found through
Mendeley Data's public file API. The sheet is read row by row and only January 2020 is kept.
Power is the average 10-minute output in kW. The record states no time zone and not which end
of the interval a stamp marks, so the index is the stamp as published, a naive `time`, not
UTC; no daylight-saving gaps or repeats appear, which fits UTC. Traps handled:
- the power column holds impossible spikes (from -3,275 to 3,149 kW, against a ceiling near
  851 kW), so values outside -100 to 1,000 kW are dropped;
- some timestamps appear twice with different rows; both copies are dropped.
Not fixable in code: the turbine is behind the meter, and it produced nothing from October 2018
to July 2019 during a gearbox change.
"""

import io

import openpyxl
import pandas as pd
import requests

API = "https://data.mendeley.com/public-api/datasets/tm988rs48k/files"
FIRST, STOP = pd.Timestamp("2020-01-01"), pd.Timestamp("2020-02-01")

listing = requests.get(API, params={"folder_id": "root", "version": 2}, timeout=60).json()
xlsx = next(f for f in listing if f["filename"].endswith(".xlsx"))
resp = requests.get(xlsx["content_details"]["download_url"], timeout=300)
resp.raise_for_status()

sheet = openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True).active
rows = sheet.iter_rows(values_only=True)
header = next(rows)
keep = []
for row in rows:  # rows run in time order
    if row[0] >= STOP:
        break
    if row[0] >= FIRST:
        keep.append(row)
raw = pd.DataFrame(keep, columns=header)

raw = raw[~raw["Timestamps"].duplicated(keep=False)]  # repeated stamps: drop both
raw = raw[raw["Power"].between(-100, 1000)]  # remove impossible spikes
df = (
    raw.assign(time=pd.to_datetime(raw["Timestamps"]))  # zone and stamp end not stated
    .rename(columns={"Power": "power_kw", "WindSpeed": "wind_speed_ms"})
    .set_index("time")
    .sort_index()[["power_kw", "wind_speed_ms"]]
)
print(df)
print(f"{len(df)} ten-minute rows, mean {df['power_kw'].mean():.0f} kW, "
      f"{df['power_kw'].sum() / 6 / 1000:.1f} MWh")  # kW x 1/6 h
