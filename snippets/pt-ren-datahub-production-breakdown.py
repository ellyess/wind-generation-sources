# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Mainland Portugal wind generation (MW) per quarter hour for one day from the REN DataHub API.

One request per day returns chart JSON: clock labels "00:00" to "23:45" and a "Wind" series in
MW, onshore and the floating offshore farm together. Traps handled:
- the labels carry no offset; they behave as Lisbon local time, but REN does not say so, so
  they are kept as a naive `time`, not converted to UTC;
- the sample is the autumn clock change, 26 October 2025, with 100 labels: "01:00" to "01:45"
  appear twice (in order, summer time first), so the naive index repeats there.
On the spring change (92 labels) the skipped hour is simply absent. REN does not say whether a
label starts or ends its quarter hour, or whether a value is an average; labels are kept as
published, and no energy total is formed. REN's terms forbid re-hosting the series without
permission.
"""

import pandas as pd
import requests

DAY = "2025-10-26"

resp = requests.get(
    "https://servicebus.ren.pt/datahubapi/electricity/ElectricityProductionBreakdownDaily",
    params={"culture": "en-US", "date": DAY},
    timeout=60,
)
resp.raise_for_status()
chart = resp.json()
wind = next(s for s in chart["series"] if s["name"] == "Wind")

local = pd.to_datetime(DAY + " " + pd.Series(chart["xAxis"]["categories"]))
df = pd.DataFrame({
    "time": local,  # zone and stamp end not stated
    "wind_mw": wind["data"],
}).set_index("time")
print(df)
print(f"{len(df)} quarter-hours, mean {df['wind_mw'].mean():,.0f} MW, "
      f"peak {df['wind_mw'].max():,.0f} MW")
