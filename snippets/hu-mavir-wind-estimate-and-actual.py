# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32", "openpyxl>=3.1"]
# ///
"""Hungarian national wind output per quarter hour for one day, from MAVIR chart 11840.

The xlsx export (the endpoint MAVIR's chart page calls) holds three forecasts and four "actual"
columns with no unit in the headers; magnitudes and MAVIR's chart fit average MW per quarter
hour. Traps handled:
- each stamp carries its own UTC offset ("2025.10.26 02:45:00 +0200"), so the offset is read
  rather than the clock time, which repeats on the autumn change day (this sample has 100
  quarter hours);
- stamps behave as the end of each quarter hour (a day runs 00:15 to 24:00), observed in the
  data rather than documented, so they are moved back 15 minutes to the period start;
- the actual columns disagree by 10 to 16 per cent, so one is chosen: net commercial
  settlement metering, the only one that goes back to 2015. Forecast columns are left out so
  that observed and forecast values are not mixed.
"""

import io

import pandas as pd
import requests

# Epoch milliseconds: local midnight 26 Oct 2025 (UTC+2) to local midnight 27 Oct (UTC+1)
FROM_MS, TO_MS = 1761429600000, 1761519600000
SETTLEMENT = "Szélerőművek tény - nettó kereskedelmi elszámolási"

resp = requests.get(
    "https://rtdwweb.mavir.hu/rtdwweb/webuser/chart/11840/export",
    params={"exportType": "xlsx", "fromTime": FROM_MS, "toTime": TO_MS,
            "periodType": "min", "period": 15},
    timeout=60,
)
resp.raise_for_status()  # HTTP 429 means too many requests: wait a minute
rows = pd.read_excel(io.BytesIO(resp.content)).dropna(subset=[SETTLEMENT])

end = pd.to_datetime(rows["Időpont"], format="%Y.%m.%d %H:%M:%S %z", utc=True)
df = (
    rows.assign(time_utc=end - pd.Timedelta(minutes=15))  # period end -> period start
    .set_index("time_utc")
    .sort_index()[[SETTLEMENT]]
    .rename(columns={SETTLEMENT: "wind_mw"})
)
print(df)
print(f"{len(df)} quarter-hours, {df['wind_mw'].sum() * 0.25 / 1000:.2f} GWh")  # MW x 0.25 h
