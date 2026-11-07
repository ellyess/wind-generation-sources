# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""France national wind output for one day from RTE's eCO2mix consolidated data (via ODRE).

The eolien column is onshore and offshore together, in MW, every half hour. RTE does not say
whether a value is a mean or a snapshot, or whether the stamp opens or closes the half hour, so
the stamps are kept as published (date_heure, in UTC). Traps handled: the empty quarter-hour
rows (:15 and :45) are dropped; on the March clock change the hour that did not exist is a copy
of the next hour under the same UTC stamp, so duplicated stamps are dropped; on the October
change one UTC hour has no rows, so the series is reindexed and that hour is left missing
(NaN), not interpolated. The sample is 27 October 2024, which shows the gap.
"""

import pandas as pd
import requests

DAY = "2024-10-27"  # a French local date

resp = requests.get(
    "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "eco2mix-national-cons-def/exports/json",
    params={"select": "date_heure,heure,eolien", "where": f"date='{DAY}'",
            "order_by": "date_heure"},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()).dropna(subset=["eolien"])

wind = (
    rows.assign(time_utc=pd.to_datetime(rows["date_heure"], utc=True))
    .drop_duplicates("time_utc")
    .set_index("time_utc")["eolien"]
    .astype(float)
)
full = pd.date_range(wind.index.min(), wind.index.max(), freq="30min", name="time_utc")
df = wind.reindex(full).to_frame("wind_mw")
print(df)
gwh = df["wind_mw"].sum() * 0.5 / 1000  # MW x 0.5 h, if each value is a half-hour mean
print(f"{len(df)} half-hours ({df['wind_mw'].isna().sum()} missing), about {gwh:.1f} GWh")
