# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pyarrow>=15", "requests>=2.32"]
# ///
"""Ten-minute active power of the six Altahullion 2 turbines with data, 4 September 2025 to
1 March 2026, from the RES/TRIG Altahullion open dataset on Zenodo.

turbine_data.zip (47 MB) holds the 10-minute statistics as one parquet file, with a two-level
column index of station id and signal. ActPower_Value_mean is the 10-minute mean active power;
the unit is not stated, but values peak at the 1,330 kW rating, so it is read as kW. Traps
handled: columns are keyed by station id, so they are mapped to turbine names with the metadata
file; only six of the 29 turbines have data, so no farm total is formed. The time zone and
which end of the period the stamp marks are not stated, so the index is left as a naive `time`,
not UTC. The stamps run straight through the 26 October 2025 clock change with no repeated
hour, as a UTC clock would, but a local logger that overwrote that hour would look the same.
"""

import io
import zipfile

import pandas as pd
import requests

RECORD = "https://zenodo.org/records/19948235/files"
FILE = "turbine_data/scada_df_ALTA2_20250904_20260301.parquet"

meta = pd.read_csv(f"{RECORD}/Altahullion_turbine_metadata.csv", encoding="utf-8-sig",
                   dtype={"Station ID": "string"})
names = dict(zip(meta["Station ID"], meta["Turbine Name"], strict=True))

resp = requests.get(f"{RECORD}/turbine_data.zip", timeout=300)
resp.raise_for_status()
scada = pd.read_parquet(io.BytesIO(zipfile.ZipFile(io.BytesIO(resp.content)).read(FILE)))

power = scada.xs("ActPower_Value_mean", axis=1, level=1)
df = (
    power.rename(columns=names)
    .rename_axis(index="time", columns="unit_id")
    .stack()
    .rename("power_kw")
    .reset_index("unit_id")
    .sort_index()
)
print(df)
mwh = df["power_kw"].sum() / 6 / 1000  # kW x 1/6 h -> kWh -> MWh
print(f"{len(df)} turbine-10-minutes over {df['unit_id'].nunique()} turbines, {mwh:.0f} MWh")
