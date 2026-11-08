# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Finnish wind output for one day from Fingrid Open Data, dataset 75 (15-minute wind generation).

Each row is wind generation in MW for Finland over one interval, with startTime and endTime in
UTC; the start is used. Fingrid measures most parks and estimates the rest (about two percent of
capacity), and does not say whether a value is a mean or a reading.

Traps handled:
- The API returns 10 rows a page and the newest first by default; the snippet asks for one page
  of up to 20,000 rows in ascending order, and stops if more pages remain.
- Dataset 75 is hourly before 13 June 2023 and 15-minute after, so each row keeps its own
  length in hours (endTime - startTime), not a fixed step. No energy total is formed, because
  Fingrid does not say whether a value is a mean.

Written from https://data.fingrid.fi/en/instructions and the developer portal's operation
definition (https://developer-data.fingrid.fi/, GetDatasetData) on 2026-11-07; not yet run with
a key. Without a key the API answers 401, "Access denied due to missing subscription key".
"""
# wgs: needs FINGRID_API_KEY

import os

import pandas as pd
import requests

DAY = "2024-01-15"  # a UTC day; the API takes and returns UTC

resp = requests.get(
    "https://data.fingrid.fi/api/datasets/75/data",
    headers={"x-api-key": os.environ["FINGRID_API_KEY"]},  # a header, not the URL, per Fingrid
    params={"startTime": f"{DAY}T00:00:00Z", "endTime": f"{DAY}T23:59:00Z", "format": "json",
            "pageSize": 20000, "sortBy": "startTime", "sortOrder": "asc"},
    timeout=60,
)
resp.raise_for_status()
body = resp.json()
assert body["pagination"]["nextPage"] is None, "more pages: ask for a shorter period"
rows = pd.DataFrame(body["data"])

start, end = (pd.to_datetime(rows[c], utc=True) for c in ("startTime", "endTime"))
df = (
    pd.DataFrame({"time_utc": start, "wind_mw": rows["value"],
                  "hours": (end - start) / pd.Timedelta("1h")})
    .set_index("time_utc").sort_index()
)
print(df)
print(f"{len(df)} intervals, mean {df['wind_mw'].mean():,.0f} MW, "
      f"peak {df['wind_mw'].max():,.0f} MW")
