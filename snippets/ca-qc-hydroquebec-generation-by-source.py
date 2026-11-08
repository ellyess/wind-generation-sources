# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Quebec's hourly wind output for one day from Hydro-Québec's open-data portal.

The history dataset gives telemetered wind output in MW (column "eolien") once an hour, with
stamps the portal defines as the time the measurement was taken; it does not say whether a value
is a snapshot or an hourly mean. Wind covers only independent producers selling all their
output to Hydro-Québec. Traps handled: stamps are requested in UTC (timezone=UTC), not the
dataset's America/Toronto default; on the autumn clock change, 2 November 2025 used here, the
UTC hour 05:00 is missing and 06:00 appears twice with different values, so both rows of a
repeated stamp are dropped and the day is rebuilt on a continuous hourly UTC index, leaving the
unknown hours empty rather than guessing which value is which; blank wind values stay missing.
"""

import pandas as pd
import requests

DAY, NEXT = "2025-11-02", "2025-11-03"  # an autumn clock-change day, to show the repeat

resp = requests.get(
    "https://donnees.hydroquebec.com/api/explore/v2.1/catalog/datasets/"
    "historique-production-electricite-quebec/records",
    params={"select": "date,eolien", "timezone": "UTC", "order_by": "date", "limit": 100,
            "where": f"date >= '{DAY}T00:00:00Z' and date < '{NEXT}T00:00:00Z'"},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["results"])
rows["time_utc"] = pd.to_datetime(rows["date"], utc=True)

repeated = rows["time_utc"].duplicated(keep=False)
hours = pd.date_range(f"{DAY}T00:00Z", periods=24, freq="h", name="time_utc")
df = (
    rows[~repeated].set_index("time_utc")[["eolien"]]
    .rename(columns={"eolien": "wind_mw"})
    .reindex(hours)
)
print(df)
print(f"{len(df)} hours ({df['wind_mw'].isna().sum()} unknown, {repeated.sum()} rows dropped as "
      f"repeated stamps), mean {df['wind_mw'].mean():.0f} MW, "
      f"peak {df['wind_mw'].max():.0f} MW")  # MW, not energy: the value type is not stated
