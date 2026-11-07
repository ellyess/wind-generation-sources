# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Great Britain wind output for January 2020 from the Open Power System Data time series package,
final version 2020-10-06.

The 30-minute file (39 MB, the smallest of the package's CSVs) holds the zones published at
half-hour resolution, Great Britain among them. utc_timestamp is the start of each period in
UTC; wind columns are in MW, split into onshore and offshore (GB capacity columns are empty in
2020). OPSD does not say whether a value is a mean of finer data. Traps handled: the version is
pinned by its dated URL (cite its DOI, 10.25832/time_series/2020-10-06), because the final
version holds only ENTSO-E data from 2015 and stops at 30 September 2020; older versions hold
longer TSO-sourced series.
"""

import io

import pandas as pd
import requests

URL = ("https://data.open-power-system-data.org/time_series/2020-10-06/"
       "time_series_30min_singleindex.csv")
COLS = {"GB_GBN_wind_generation_actual": "wind_mw",
        "GB_GBN_wind_onshore_generation_actual": "onshore_mw",
        "GB_GBN_wind_offshore_generation_actual": "offshore_mw"}

resp = requests.get(URL, timeout=300)
resp.raise_for_status()
rows = pd.read_csv(io.BytesIO(resp.content), usecols=["utc_timestamp", *COLS])

df = (
    rows.assign(time_utc=pd.to_datetime(rows["utc_timestamp"], utc=True))
    .set_index("time_utc")
    .rename(columns=COLS)
    .loc["2020-01", list(COLS.values())]
)
print(df)
gwh = df["wind_mw"].sum() * 0.5 / 1000  # MW x 0.5 h, if each value is a half-hour mean
print(f"{len(df)} half-hours, about {gwh:.0f} GWh (mean {df['wind_mw'].mean():.0f} MW)")
