# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly energy per unit for one Australian wind farm and day from the Open Electricity API.

GET /v4/data/facilities/NEM returns one series per unit (columns.unit_code), each a list of
[timestamp, value] pairs. "energy" is MWh, summed from 5-minute values that Open Electricity
computes from AEMO SCADA power (MW) with the trapezoidal rule. Timestamps come in network-local
time with an offset (NEM is fixed UTC+10, no daylight saving) and are converted to UTC here.
Open Electricity does not say whether a stamp opens or closes its hour; it is kept as sent.

Traps handled:
- Request dates are naive network-local times, so the day below is an AEST day, not UTC.
- The free Community plan reaches back two years only (older dates return 400), so the sample
  is a recent day.

Written from https://docs.openelectricity.org.au/api-reference/overview and its OpenAPI
specification (https://docs.openelectricity.org.au/openapi.json) on 2026-11-07; not yet run with
a key. Without a key the endpoint answers 401 "Not authenticated".
"""
# wgs: needs OPENELECTRICITY_API_KEY

import os

import pandas as pd
import requests

FACILITY = "GPWFEST"  # Golden Plains East wind farm, Victoria (the docs' example facility)
START, END = "2025-06-15T00:00:00", "2025-06-16T00:00:00"  # AEST (UTC+10), naive as required

resp = requests.get(
    "https://api.openelectricity.org.au/v4/data/facilities/NEM",
    headers={"Authorization": f"Bearer {os.environ['OPENELECTRICITY_API_KEY']}"},
    params={"facility_code": FACILITY, "metrics": "energy", "interval": "1h",
            "date_start": START, "date_end": END},
    timeout=60,
)
resp.raise_for_status()
series = resp.json()["data"][0]  # one block per metric; only energy was asked for
assert series["unit"] == "MWh", series["unit"]

rows = pd.DataFrame(
    [(r["columns"]["unit_code"], t, v) for r in series["results"] for t, v in r["data"]],
    columns=["unit_id", "time", "wind_mwh"],
)
df = (
    rows.assign(time_utc=pd.to_datetime(rows["time"], utc=True))  # stamps carry +10:00
    .set_index("time_utc")
    .sort_index()[["unit_id", "wind_mwh"]]
)
print(df)
print(f"{len(df)} unit-hours, {df['unit_id'].nunique()} units, "
      f"{df['wind_mwh'].sum() / 1000:.2f} GWh")
