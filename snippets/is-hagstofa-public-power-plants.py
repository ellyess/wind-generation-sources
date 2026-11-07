# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Icelandic annual wind capacity and generation, Statistics Iceland table IDN02101 (to 2019).

A PxWeb query for the wind sector returns installed capacity at year end in MW and annual
generation in GWh. Traps handled:
- years before wind existed come back as "." and are dropped as missing, leaving 2013 to 2019;
  the table stops in 2019 and covers only a few turbines;
- values use a point decimal with three places ("8.400" is 8.4 GWh), read as decimals;
- the API rate-limits hard (HTTP 429), so the request is retried after a pause.
"""

import io
import time

import pandas as pd
import requests

URL = ("https://px.hagstofa.is/pxen/api/v1/en/Umhverfi/4_orkumal/2_framleidslaognotkun/"
       "IDN02101.px")
query = {
    "query": [
        {"code": "Eining", "selection": {"filter": "item", "values": ["Q"]}},  # quantity
        {"code": "Tegund", "selection": {"filter": "item", "values": ["4"]}},  # wind energy
    ],
    "response": {"format": "csv"},
}

for _attempt in range(6):
    resp = requests.post(URL, json=query, timeout=60)
    if resp.status_code != 429:
        break
    time.sleep(30)  # "Too many requests in too short timeframe"
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.text), na_values=".")

df = (
    rows.set_axis(["unit", "period", "capacity_mw", "wind_gwh"], axis=1)
    .dropna(subset=["wind_gwh"])
    .astype({"period": str})
    .set_index("period")[["capacity_mw", "wind_gwh"]]
)
print(df)
print(f"{len(df)} years, {df['wind_gwh'].sum():.1f} GWh")
