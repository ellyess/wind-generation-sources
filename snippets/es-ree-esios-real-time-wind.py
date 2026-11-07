# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Mainland Spain real-time wind output for one day from REE's ESIOS API (indicator 551).

551 is control-centre telemetry of wind generation in MW for the peninsular system only (the
islands, Ceuta and Melilla are not in it). Each value has a local "datetime" with its offset and
a "datetime_utc"; the UTC one is used. REE does not say whether a value is a snapshot or a
five-minute mean, nor whether a stamp opens or closes its interval; it is read here as the start.

Traps handled:
- This is power in MW, not metered energy; energy is MW x the time step. Older periods are at
  10 minutes rather than 5, so the step is taken from the stamps rather than assumed.
- The day asked for is a Madrid day, given in UTC (23:00Z to 23:00Z in winter).

Written from https://api.esios.ree.es/ (indicator pages) on 2026-11-07; not yet run with a key.
Without a token the API answers 403 "Forbidden". The documentation's examples send the token in
an x-api-key header wrapped in double quotes, and so does this snippet.
"""
# wgs: needs ESIOS_API_KEY

import os

import pandas as pd
import requests

START, END = "2025-01-14T23:00:00Z", "2025-01-15T22:59:59Z"  # 15 January 2025, Madrid time

resp = requests.get(
    "https://api.esios.ree.es/indicators/551",
    headers={"Accept": "application/json; application/vnd.esios-api-v1+json",
             "Content-Type": "application/json",
             "x-api-key": f'"{os.environ["ESIOS_API_KEY"]}"'},
    params={"start_date": START, "end_date": END},
    timeout=60,
)
resp.raise_for_status()
values = pd.DataFrame(resp.json()["indicator"]["values"])
assert values["geo_id"].nunique() == 1, "more than one area: sum them or pick one"

df = (
    values.assign(time_utc=pd.to_datetime(values["datetime_utc"], utc=True))
    .set_index("time_utc")
    .sort_index()[["value"]]
    .rename(columns={"value": "wind_mw"})
)
step_h = df.index.to_series().diff().median() / pd.Timedelta("1h")  # 5 or 10 minutes
print(df)
print(f"{len(df)} intervals of {step_h * 60:.0f} min, "
      f"{df['wind_mw'].sum() * step_h / 1000:.1f} GWh")  # MW x step
