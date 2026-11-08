# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""South African hourly wind from Eskom's data portal (Hourly_Generation.csv).

The public CSV is a rolling window of the previous and current month, national, with columns
"Date Time Hour Beginning, Wind, PV, CSP, Other RE". Traps handled:
- the page's download link can point at a stale upload folder and return 404, so the path is
  built from the current year and month, falling back to the previous month;
- hours not yet reached are filled with zeros; trailing all-zero rows are dropped;
- stamps mark the start of each hour.
Eskom states neither the time zone nor the unit, so stamps are kept as a naive `time`, not UTC
(South African Standard Time, UTC+02:00, fits the solar column's sunrise but is not stated), and
the values are read as average MW, which their size against about 4.2 GW of installed wind
supports (an assumption). Only wind that Eskom owns or contracts is included. There is no
stable dated file.
"""

import io

import pandas as pd
import requests

BASE = "https://www.eskom.co.za/dataportal/wp-content/uploads/{:%Y/%m}/Hourly_Generation.csv"

now = pd.Timestamp.now(tz="Africa/Johannesburg")
for month in (now, now - pd.DateOffset(months=1)):
    resp = requests.get(BASE.format(month), timeout=60)
    if resp.ok:
        break
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.text))

stamp = pd.to_datetime(rows["Date Time Hour Beginning"])  # zone not stated
df = (
    rows.assign(time=stamp)
    .set_index("time")
    .sort_index()[["Wind"]]
    .rename(columns={"Wind": "wind_mw"})
)
live = rows.drop(columns="Date Time Hour Beginning").ne(0).any(axis=1).to_numpy()
df = df.iloc[: live.nonzero()[0].max() + 1]  # cut the zero-filled future hours
print(df)
print(f"{len(df)} hours, {df['wind_mw'].sum() / 1000:.1f} GWh (if the values are MW)")
