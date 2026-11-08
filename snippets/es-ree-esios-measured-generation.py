# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Spanish metered wind energy for one day from REE's ESIOS API (indicators 1159 and 1160).

1159 is onshore and 1160 offshore metered generation, hourly MWh, published by province. The API
is asked to sum the provinces to Spain (geo_trunc=country) and to sum within each hour. Each
value has a local "datetime" with its offset and a "datetime_utc"; the UTC one is used. REE does
not say whether a stamp opens or closes its hour; the analysis page lists a day as 00:00 to
23:00, which fits the start, but the stamp is kept as published.

Traps handled:
- The combined indicator 10037 is empty in older years, so onshore 1159 and offshore 1160 are
  fetched separately and added.
- Meter readings arrive from the month after (M+1), so the sample is a past month; a recent day
  would come back empty or incomplete.
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
HEADERS = {"Accept": "application/json; application/vnd.esios-api-v1+json",
           "Content-Type": "application/json",
           "x-api-key": f'"{os.environ["ESIOS_API_KEY"]}"'}

series = {}
for indicator, column in [(1159, "onshore_mwh"), (1160, "offshore_mwh")]:
    resp = requests.get(
        f"https://api.esios.ree.es/indicators/{indicator}", headers=HEADERS, timeout=60,
        params={"start_date": START, "end_date": END, "time_trunc": "hour", "time_agg": "sum",
                "geo_trunc": "country", "geo_agg": "sum"},
    )
    resp.raise_for_status()
    values = pd.DataFrame(resp.json()["indicator"]["values"])
    if values.empty:
        continue  # nothing metered yet, or no offshore output
    series[column] = values.set_index(pd.to_datetime(values["datetime_utc"], utc=True))["value"]

df = pd.DataFrame(series).fillna(0.0).rename_axis("time_utc").sort_index()
df["wind_mwh"] = df.sum(axis=1)
print(df)
print(f"{len(df)} hours, {df['wind_mwh'].sum() / 1000:.1f} GWh")  # already energy per hour
