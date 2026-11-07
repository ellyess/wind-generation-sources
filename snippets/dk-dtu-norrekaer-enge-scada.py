# /// script
# requires-python = ">=3.11"
# dependencies = ["netCDF4>=1.6", "pandas>=2.2", "requests>=2.32", "xarray>=2024.1"]
# ///
"""Per-turbine 10-minute mean power at Nørrekær Enge II, 1992-1993, from DTU Data.

Reads norre_m2_concurent.nc (12 MB, the records where all signals are present) and keeps the
40 active power variables (<turbine>_pow, kW, DEIF watt converters) in long form. Traps
handled: the file has 40 turbines, not the 42 in the description, so turbine ids come from the
variable names; the time unit ("minutes since 1992-03-02 18:01:00") names no zone, and nothing
says whether a stamp opens or closes its period, so the index is left as naive `time` and not
converted to UTC; the record has gaps, so the total is over the records present. The quality
flags are all 0 ("not checked") in this file. Licence: CC BY NC 4.0 inside the file.
"""

import tempfile
from pathlib import Path

import requests
import xarray as xr

URL = "https://ndownloader.figshare.com/files/33904181"  # norre_m2_concurent.nc

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "norre_m2_concurent.nc"
    resp = requests.get(URL, timeout=120)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    with xr.open_dataset(path) as ds:
        power = [v for v in ds.data_vars if v.endswith("_pow")]
        assert all(ds[v].attrs["units"] == "kW" for v in power)
        wide = ds[power].to_dataframe()

df = (
    wide.rename(columns=lambda c: c.removesuffix("_pow"))
    .rename_axis(columns="unit_id")
    .stack()
    .rename("power_kw")
    .reset_index("unit_id")
)
df.index.name = "time"  # zone not stated by the publisher
print(df)
mwh = df["power_kw"].sum() / 6 / 1000  # kW x 1/6 h
print(f"{len(df)} turbine-records, {df['unit_id'].nunique()} turbines, {mwh:.0f} MWh recorded")
