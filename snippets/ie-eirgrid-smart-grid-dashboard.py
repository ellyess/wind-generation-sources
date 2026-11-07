# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""All-island (Ireland plus Northern Ireland) wind output for one day, EirGrid Smart Grid Dashboard.

The dashboard's JSON service (undocumented; it is what the wind page calls) gives an estimate of
all wind farms' output in MW per quarter hour, stamped in Irish local wall-clock time with no
zone. EirGrid does not say whether a value is an average or a snapshot, or which end of the
quarter hour the stamp marks; the day runs 00:00 to 23:45, so stamps are read as period starts.
Traps handled:
- the stamps are local time, converted here to UTC;
- on the autumn clock-change day the repeated 01:00 to 02:00 hour appears only once, and which
  of the two it is cannot be told, so those four values are dropped rather than guessed (the
  sample day, 26 October 2025, shows this); the missing spring hour comes back empty and is
  dropped too;
- the service often answers HTTP 503, so the request is retried after a pause.
"""

import time

import pandas as pd
import requests

DAY = "26-Oct-2025"  # an autumn clock-change day
URL = "https://www.smartgriddashboard.com/DashboardService.svc/data"
params = {"area": "windactual", "region": "ALL",
          "datefrom": f"{DAY} 00:00", "dateto": f"{DAY} 23:45"}

for _attempt in range(10):
    resp = requests.get(URL, params=params, timeout=60)
    if resp.status_code != 503:
        break
    time.sleep(20)  # "Service Unavailable" is common; wait and retry
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["Rows"]).dropna(subset=["Value"])

local = pd.to_datetime(rows["EffectiveTime"], format="%d-%b-%Y %H:%M:%S")
utc = local.dt.tz_localize("Europe/Dublin", ambiguous="NaT", nonexistent="NaT")
dropped = utc.isna().sum()
df = (
    rows.assign(time_utc=utc.dt.tz_convert("UTC"))
    .dropna(subset=["time_utc"])
    .set_index("time_utc")
    .sort_index()[["Value"]]
    .rename(columns={"Value": "wind_mw"})
)
print(df)
print(f"{len(df)} quarter-hours ({dropped} ambiguous dropped), "
      f"{df['wind_mw'].sum() * 0.25 / 1000:.1f} GWh")  # MW x 0.25 h
