# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Danish settled wind energy per price area for one day from Energinet's Energi Data Service.

ProductionConsumptionSettlement gives metered energy (MWh) per hour, stamped by HourUTC at the
start of the hour. Traps handled: the start and end parameters are read as Danish local time,
so the sample is the local day of the October clock change (25 hours); wind is split over four
size-class columns, summed here into onshore and offshore; limit=0 lifts the 100-row default.
Values are revised for up to two years, so this is a snapshot.
"""

import pandas as pd
import requests

DAY, NEXT = "2025-10-26", "2025-10-27"  # Danish local dates; 26 October has 25 hours

resp = requests.get(
    "https://api.energidataservice.dk/dataset/ProductionConsumptionSettlement",
    params={"start": DAY, "end": NEXT, "limit": 0},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["records"])

df = (
    rows.assign(
        time_utc=pd.to_datetime(rows["HourUTC"]).dt.tz_localize("UTC"),  # no Z suffix in JSON
        onshore_wind_mwh=rows["OnshoreWindLt50kW_MWh"] + rows["OnshoreWindGe50kW_MWh"],
        offshore_wind_mwh=rows["OffshoreWindLt100MW_MWh"] + rows["OffshoreWindGe100MW_MWh"],
    )
    .rename(columns={"PriceArea": "price_area"})
    .set_index("time_utc")
    .sort_index()[["price_area", "onshore_wind_mwh", "offshore_wind_mwh"]]
)
df["wind_mwh"] = df["onshore_wind_mwh"] + df["offshore_wind_mwh"]
print(df)
print(f"{len(df)} area-hours ({df.index.nunique()} hours), {df['wind_mwh'].sum() / 1000:.1f} GWh")
