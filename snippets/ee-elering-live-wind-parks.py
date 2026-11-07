# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Estonian wind parks output for one day from Elering Live's /api/system.

The wind series is the field production_renewable, which the dashboard plots as wind parks
production ("Tuuleparkide toodang"), in MW. Stamps are Unix seconds, so UTC. Elering does not
say whether a value is a mean or a snapshot, or whether the stamp opens or closes its step, so
the stamp is kept as given. Trap handled: the 5-minute grid is kept but most slots are empty
(hourly values in 2020 to 2025, quarter-hourly in 2026), so nulls are dropped.
"""

import pandas as pd
import requests

resp = requests.get(
    "https://dashboard.elering.ee/api/system",
    params={"start": "2025-06-09T21:00:00.000Z", "end": "2025-06-10T20:59:59.999Z"},  # local day
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["data"])

df = (
    rows.dropna(subset=["production_renewable"])
    .assign(time_utc=lambda d: pd.to_datetime(d["timestamp"], unit="s", utc=True))
    .set_index("time_utc")
    .sort_index()[["production_renewable"]]
    .rename(columns={"production_renewable": "wind_mw"})
)
print(df)
step_h = df.index.to_series().diff().median() / pd.Timedelta(hours=1)
print(f"{len(df)} values every {step_h:g} h, about {df['wind_mw'].sum() * step_h:.0f} MWh")
