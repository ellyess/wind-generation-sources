# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Metered output of every transmission-registered wind unit in Great Britain for one
settlement day, from Elexon's B1610 dataset.

B1610 gives the metered energy (MWh) per unit per 30-minute settlement period. Traps handled:
the values are MWh per half hour, so they are doubled to give average MW; halfHourEndTime is
the UTC end of the half hour, so 30 minutes are subtracted to stamp the start; the dataset
covers every balancing unit with no fuel label, so wind units are picked from the reference
list (fuelType WIND); the settlement run type (II, R1 to R3, RF, DF) is kept, because early
values are replaced by later runs. The sample is 31 March 2024, a clock-change day with 46
settlement periods, so times come from halfHourEndTime and never from the period number.
"""

import pandas as pd
import requests

DAY = "2024-03-31"  # a settlement date, which follows UK local time
API = "https://data.elexon.co.uk/bmrs/api/v1"

units = pd.DataFrame(requests.get(f"{API}/reference/bmunits/all", timeout=60).json())
wind = (units.loc[units["fuelType"] == "WIND", ["elexonBmUnit", "generationCapacity"]]
        .dropna().drop_duplicates("elexonBmUnit"))  # the list repeats T_WLNYO-4

resp = requests.get(f"{API}/datasets/B1610/stream",
                    params={"from": f"{DAY}T00:00Z", "to": f"{DAY}T23:00Z"}, timeout=120)
resp.raise_for_status()
rows = pd.DataFrame(resp.json())
rows = rows[rows["settlementDate"] == DAY].merge(wind, left_on="bmUnit", right_on="elexonBmUnit")

df = (
    rows.assign(
        time_utc=pd.to_datetime(rows["halfHourEndTime"], utc=True) - pd.Timedelta("30min"),
        wind_mwh=rows["quantity"],
        wind_mw=rows["quantity"] * 2,  # MWh in half an hour -> average MW
        capacity_mw=rows["generationCapacity"].astype(float),  # current registration
    )
    .rename(columns={"bmUnit": "unit_id", "settlementRunType": "run"})
    .set_index("time_utc")
    .sort_index()[["unit_id", "wind_mw", "wind_mwh", "capacity_mw", "run"]]
)
print(df)
periods = df.index.nunique()
print(f"{len(df)} unit-half-hours over {periods} periods and {df['unit_id'].nunique()} units, "
      f"{df['wind_mwh'].sum() / 1000:.1f} GWh")
