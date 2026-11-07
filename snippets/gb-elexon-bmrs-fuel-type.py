# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Great Britain wind output for one day from Elexon's FUELHH dataset.

FUELHH gives average MW over each 30-minute settlement period, stamped at the period start in
UTC. It has one wind category (no onshore/offshore split; use AGPT for that).
"""

import pandas as pd
import requests

DAY = "2024-01-15"  # a settlement date, which follows UK local time

resp = requests.get(
    "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH",
    params={"settlementDateFrom": DAY, "settlementDateTo": DAY, "fuelType": "WIND",
            "format": "json"},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["data"])

df = (
    rows.assign(time_utc=pd.to_datetime(rows["startTime"], utc=True))
    .set_index("time_utc")
    .sort_index()[["generation"]]
    .rename(columns={"generation": "wind_mw"})
)
print(df)
print(f"{len(df)} half-hours, {df['wind_mw'].sum() * 0.5 / 1000:.1f} GWh")  # MW x 0.5 h
