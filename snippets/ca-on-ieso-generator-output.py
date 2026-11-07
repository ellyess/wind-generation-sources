# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly output of every Ontario wind generator of 20 MW or more for one month (IESO).

The monthly Generator Output and Capability CSV has one row per generator, day and measurement,
with columns Hour 1 to Hour 24. IESO documents Hour as "hour ending" and the output as the
average of the hour's five-minute outputs, in MW. Traps handled: hour-ending numbers become
period starts (Hour 1 is 00:00 to 01:00); only the "Output" rows are kept, not "Available
Capacity" (nameplate minus outages) or "Forecast"; telemetry faults written "N/A" become
missing; only the unversioned file is read, because the _vN files are month-to-date copies of
it. The time zone is not stated: every day has exactly 24 hours, including clock-change days,
so the hours are read here as Eastern Standard Time (fixed UTC-05:00). That is an inference.
"""

import io

import pandas as pd
import requests

MONTH = "202610"
URL = ("https://reports-public.ieso.ca/public/GenOutputCapabilityMonth/"
       f"PUB_GenOutputCapabilityMonth_{MONTH}.csv")

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
rows = pd.read_csv(io.BytesIO(resp.content), skiprows=3, index_col=False)  # rows end in ","
rows = rows[(rows["Fuel Type"] == "WIND") & (rows["Measurement"] == "Output")]

long = rows.melt(id_vars=["Delivery Date", "Generator"],
                 value_vars=[f"Hour {h}" for h in range(1, 25)], value_name="wind_mw")
hour_start = long["variable"].str.removeprefix("Hour ").astype(int) - 1
local = pd.to_datetime(long["Delivery Date"]) + pd.to_timedelta(hour_start, unit="h")
df = (
    long.assign(time_utc=local.dt.tz_localize("Etc/GMT+5").dt.tz_convert("UTC"),
                wind_mw=pd.to_numeric(long["wind_mw"], errors="coerce"))
    .rename(columns={"Generator": "unit_id"})
    .set_index("time_utc")
    .sort_index()[["unit_id", "wind_mw"]]
)
print(df)
print(f"{len(df)} generator-hours, {df['unit_id'].nunique()} wind generators, "
      f"{df['wind_mw'].sum() / 1e3:.0f} GWh (hourly mean MW x 1 h)")
