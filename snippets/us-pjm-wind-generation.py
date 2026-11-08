# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""PJM wind output for one day from Data Miner 2's hourly wind_gen feed (settlement data).

Each row is wind generation in MW for one area and one hour. PJM does not say whether it is the
hour's mean or a reading, so no energy total is formed. The feed gives datetime_beginning_utc and
datetime_beginning_ept; PJM's guide says "beginning" marks the start of the interval, so the UTC
start is used and Eastern prevailing time is not needed.

Traps handled:
- Areas overlap (RFC is MIDATL plus WEST, RTO is the whole system), so only RTO is kept. The
  area filter is a partial match, so the rows are also checked for an exact "RTO".
- Recent days read 0 MW until settlement catches up, so the sample is a past day.

Written from PJM's Data Miner API Guide
(https://www.pjm.com/-/media/etools/data-miner-2/data-miner-2-api-guide.ashx) on 2026-11-07;
not yet run with a key. Without a key the endpoint answers 401.
"""
# wgs: needs PJM_API_KEY

import os

import pandas as pd
import requests

DAY = "2024-01-15"  # a UTC day, well past the 90 days in which values can still change

resp = requests.get(
    "https://api.pjm.com/api/v1/wind_gen",
    headers={"Ocp-Apim-Subscription-Key": os.environ["PJM_API_KEY"]},
    params={"download": "true", "format": "json", "rowCount": 50000, "startRow": 1,
            "datetime_beginning_utc": f"{DAY} 00:00 to {DAY} 23:59", "area": "RTO"},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json())  # download=true returns the records alone
rows = rows[rows["area"] == "RTO"]

df = (
    rows.assign(time_utc=pd.to_datetime(rows["datetime_beginning_utc"], utc=True))
    .set_index("time_utc")
    .sort_index()[["wind_generation_mw"]]
    .rename(columns={"wind_generation_mw": "wind_mw"})
)
print(df)
print(f"{len(df)} hours, mean {df['wind_mw'].mean():,.0f} MW, peak {df['wind_mw'].max():,.0f} MW")
