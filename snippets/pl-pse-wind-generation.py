# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Poland national wind generation (MW) per quarter hour for one day from PSE's his-wlk-cal report.

The "wi" field is total generation of wind sources in MW, onshore and offshore together.
Traps handled:
- dtime marks the end of each quarter hour (and the last one carries the next day's date), so
  the UTC end stamp dtime_utc is moved back 15 minutes to the period start, and the day is
  selected on business_date, not on the date part of dtime;
- the sample day is the spring clock change, which has 92 quarter hours, not 96;
- PSE warns that "%24" may not be decoded to "$", so the query string is sent with a literal
  "$" and the script checks that the filter was applied.
Past days are republished: keep publication_ts with each value and re-download before final
use. PSE does not say whether a value is a quarter-hour mean or a reading; mean is assumed for
the energy total.
"""

import pandas as pd
import requests

DAY = "2026-03-29"

resp = requests.get(
    "https://api.raporty.pse.pl/api/his-wlk-cal",
    params=f"$filter=business_date eq '{DAY}'&$first=200",  # a string keeps "$" unescaped
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["value"])
assert (rows["business_date"] == DAY).all(), "filter ignored"

df = (
    rows.assign(time_utc=pd.to_datetime(rows["dtime_utc"]).dt.tz_localize("UTC")
                - pd.Timedelta(minutes=15))  # period end -> period start
    .set_index("time_utc")
    .sort_index()
    .rename(columns={"wi": "wind_mw"})[["wind_mw", "publication_ts"]]
)
print(df)
print(f"{len(df)} quarter-hours, {df['wind_mw'].sum() * 0.25 / 1000:.1f} GWh")  # MW x 0.25 h
