# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""MISO-wide hourly wind energy for 2025 from the Historical Hourly Wind Data report.

One CSV per year to date, with a MISO-wide wind total in MWh per hour. Traps handled:
- hours are "Hour Ending" 1-24 in Eastern Standard Time all year (no daylight saving), so hour
  ending h is shifted to the hour starting at h-1 on a fixed UTC-05:00 clock, then to UTC;
- the file has seven header lines above the table and a disclaimer line below it, both skipped.
This is MISO's hourly wind file, not the fuel-mix workbook with its day-ahead column.
"""

import io

import pandas as pd
import requests

URL = "https://docs.misoenergy.org/marketreports/20251231_hwd_HIST.csv"  # published 31 Dec 2025

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.text), skiprows=7, usecols=[0, 1, 2],
                   names=["day", "hour_ending", "wind_mwh"], header=0)
rows = rows[pd.to_numeric(rows["hour_ending"], errors="coerce").notna()]  # drop the disclaimer

start_est = (pd.to_datetime(rows["day"], format="%m/%d/%Y")
             + pd.to_timedelta(rows["hour_ending"].astype(int) - 1, unit="h"))
df = (
    rows.assign(time_utc=start_est.dt.tz_localize("Etc/GMT+5").dt.tz_convert("UTC"))  # = UTC-05
    .set_index("time_utc")
    .sort_index()[["wind_mwh"]]
    .astype(float)
)
print(df)
print(f"{len(df)} hours, {df['wind_mwh'].sum() / 1e6:.1f} TWh")
