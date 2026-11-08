# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""California ISO wind for one day from the Today's Outlook renewables history file.

Each daily renewables.csv gives the CAISO-wide five-minute average power in MW by renewable
source. Traps handled:
- the "Time" column is a bare Pacific clock time with no date or offset, so the snippet adds the
  date, localises to America/Los_Angeles and converts to UTC (an ordinary day is used; clock-change
  days would need the repeated or missing hour resolving);
- CAISO does not say whether a time starts or ends its interval; the yearly workbook's numbering
  reads as interval start, but that is unconfirmed, so the stamp is kept as published.
"""

import io

import pandas as pd
import requests

DAY = "2025-10-15"

resp = requests.get(
    f"https://www.caiso.com/outlook/history/{DAY.replace('-', '')}/renewables.csv", timeout=60
)
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.text))

local = pd.to_datetime(DAY + " " + rows["Time"]).dt.tz_localize("America/Los_Angeles")
df = (
    rows.assign(time_utc=local.dt.tz_convert("UTC"))
    .set_index("time_utc")
    .sort_index()[["Wind"]]
    .rename(columns={"Wind": "wind_mw"})
)
print(df)
print(f"{len(df)} five-minute intervals, {df['wind_mw'].sum() / 12 / 1000:.1f} GWh")  # MW x 1/12 h
