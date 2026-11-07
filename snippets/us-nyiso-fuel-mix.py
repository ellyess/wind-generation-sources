# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""New York State wind for one day from NYISO's Real-Time Fuel Mix (rtfuelmix) file.

One statewide value per fuel every five minutes, in MW of power (the column was once headed
"Gen MWh"; the values are power either way). The sample is 1 November 2026, when clocks went back.
Traps handled:
- stamps are local clock times with a separate EDT or EST label, so the two are combined into a
  fixed offset before converting to UTC; the repeated 01:00-01:55 hour stays in order;
- the values are MW, so energy is the sum divided by 12, not the plain sum.
NYISO does not say whether a stamp starts or ends its five minutes, or whether a value is a
snapshot or an average; the stamp is kept as given (the day's first is 00:05). Off-grid stamps
(such as 08:09:45) that NYISO sometimes adds are dropped, keeping the five-minute grid.
"""

import io

import pandas as pd
import requests

DAY = "20261101"

resp = requests.get(f"https://mis.nyiso.com/public/csv/rtfuelmix/{DAY}rtfuelmix.csv", timeout=60)
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.text))
rows = rows[rows["Fuel Category"] == "Wind"]

offset = rows["Time Zone"].map({"EDT": "-04:00", "EST": "-05:00"})
stamp = pd.to_datetime(rows["Time Stamp"] + offset, format="%m/%d/%Y %H:%M:%S%z", utc=True)
df = (
    rows.assign(time_utc=stamp)
    .set_index("time_utc")
    .sort_index()[["Gen MW"]]
    .rename(columns={"Gen MW": "wind_mw"})
)
df = df[(df.index.second == 0) & (df.index.minute % 5 == 0)]
print(df)
print(f"{len(df)} five-minute values, {df['wind_mw'].sum() / 12:.0f} MWh")  # MW x 1/12 h
