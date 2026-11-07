# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Danish five-minute onshore and offshore wind power per price area from Energi Data Service.

ElectricityProdex5MinRealtime gives MW from upscaled real-time control-system measurements, an
operational estimate rather than metered energy (use ProductionConsumptionSettlement for that).
Stamps are UTC by the column name only (Minutes5UTC, no Z suffix). The publisher does not say
whether a stamp opens or closes its five minutes, or whether a value is a mean or a snapshot,
so the stamp is kept as given. Trap handled: start and end are read as Danish local time, so
the sample is one local day and the join uses Minutes5UTC.
"""

import pandas as pd
import requests

DAY, NEXT = "2025-01-15", "2025-01-16"  # Danish local dates

resp = requests.get(
    "https://api.energidataservice.dk/dataset/ElectricityProdex5MinRealtime",
    params={"start": DAY, "end": NEXT, "limit": 0},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["records"])

df = (
    rows.assign(time_utc=pd.to_datetime(rows["Minutes5UTC"]).dt.tz_localize("UTC"))
    .rename(columns={"PriceArea": "price_area", "OnshoreWindPower": "onshore_wind_mw",
                     "OffshoreWindPower": "offshore_wind_mw"})
    .set_index("time_utc")
    .sort_index()[["price_area", "onshore_wind_mw", "offshore_wind_mw"]]
)
df["wind_mw"] = df["onshore_wind_mw"] + df["offshore_wind_mw"]
print(df)
gwh = df["wind_mw"].sum() * 5 / 60 / 1000  # MW x 5 minutes
print(f"{len(df)} area-intervals of 5 minutes, about {gwh:.1f} GWh")
