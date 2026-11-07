# /// script
# requires-python = ">=3.11"
# dependencies = ["h5netcdf>=1.3", "h5py>=3.10", "pandas>=2.2", "requests>=2.32", "xarray>=2024.1"]
# ///
"""Ten-minute SCADA power per turbine at Beberibe wind farm, Brazil (UFSC campaign, Zenodo).

UEBB_v1.nc holds one year (August 2013 to July 2014) of 10-minute means for 32 Enercon E-48
turbines (800 kW), with Time in seconds since 1970 UTC. Traps handled:
- the power variables are labelled "rpm"; the values (0 to 840) are kW, so the units attribute
  is ignored and the column is named power_kw;
- the minimum-power variable uses 65535 as an undeclared missing-value marker, which is masked.
Whether a stamp marks the start or end of its 10 minutes is not stated; the first stamp is
00:00 and the last 23:50, which reads as period start, and this snippet assumes so. Turbine
numbers 1 to 32 have no coordinates in the file. Pedra do Sal (UEPS_v1.nc, 205 MB) has the
same layout.
"""
# wgs: skip downloads 163 MB (the smaller of the two files; no smaller sample exists)

import tempfile
from pathlib import Path

import requests
import xarray as xr

URL = "https://zenodo.org/records/1475197/files/UEBB_v1.nc"

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "UEBB_v1.nc"
    with requests.get(URL, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        with path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    with xr.open_dataset(path, engine="h5netcdf") as ds:
        power = ds[["active_power_total", "active_power_total_min"]].load()

power["active_power_total_min"] = power["active_power_total_min"].where(
    power["active_power_total_min"] != 65535)
df = (
    power.to_dataframe()
    .rename(columns={"active_power_total": "power_kw", "active_power_total_min": "power_min_kw"})
    .reset_index()
    .assign(time_utc=lambda d: d["Time"].dt.tz_localize("UTC"),
            unit_id=lambda d: d["Turbine"].astype(int))
    .dropna(subset=["power_kw"])
    .set_index("time_utc")
    .sort_index()[["unit_id", "power_kw", "power_min_kw"]]
)
print(df)
print(f"{len(df)} turbine-10-minutes, {df['unit_id'].nunique()} turbines, "
      f"{df['power_kw'].sum() / 6 / 1e6:.1f} GWh, mean {df['power_kw'].mean():.0f} kW per turbine")
