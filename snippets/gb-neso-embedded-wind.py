# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""NESO's estimate of embedded (distribution-connected) wind in Great Britain for one day,
from the Historic Demand Data files, read through the portal's CKAN datastore API.

EMBEDDED_WIND_GENERATION and EMBEDDED_WIND_CAPACITY are in MW per settlement period. This is a
model estimate, not a measurement. Traps handled: rows carry only a UK local settlement date and
a period number, and clock-change days have 46 or 50 periods, so each period start is built as
local midnight in UTC plus 30 minutes per period (never by localising "date + hh:mm", which is
ambiguous in October); columns are read by name because the yearly files differ in layout;
forecast rows (FORECAST_ACTUAL_INDICATOR "F", in the current year's file) are dropped. The
sample is 27 October 2024, a 50-period day. Whether a value is a half-hour mean is not stated.
"""

import json

import pandas as pd
import requests

DAY = "2024-10-27"  # a settlement date in UK local time
RESOURCE_2024 = "f6d02c0f-957b-48cb-82ee-09003f2ba759"  # "Historic Demand Data 2024"

resp = requests.get(
    "https://api.neso.energy/api/3/action/datastore_search",
    params={"resource_id": RESOURCE_2024, "filters": json.dumps({"SETTLEMENT_DATE": DAY}),
            "limit": 100},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["result"]["records"])
if "FORECAST_ACTUAL_INDICATOR" in rows:
    rows = rows[rows["FORECAST_ACTUAL_INDICATOR"] != "F"]

midnight = pd.Timestamp(DAY, tz="Europe/London").tz_convert("UTC")
df = (
    rows.assign(time_utc=midnight + pd.to_timedelta((rows["SETTLEMENT_PERIOD"] - 1) * 30, "min"))
    .set_index("time_utc")
    .sort_index()[["EMBEDDED_WIND_GENERATION", "EMBEDDED_WIND_CAPACITY"]]
    .rename(columns={"EMBEDDED_WIND_GENERATION": "wind_mw",
                     "EMBEDDED_WIND_CAPACITY": "capacity_mw"})
)
print(df)
print(f"{len(df)} half-hours, {df['wind_mw'].sum() * 0.5 / 1000:.1f} GWh estimated "
      f"(mean {df['wind_mw'].mean():.0f} MW of {df['capacity_mw'].max():.0f} MW)")
