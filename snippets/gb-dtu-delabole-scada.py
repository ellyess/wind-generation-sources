# /// script
# requires-python = ">=3.11"
# dependencies = ["h5netcdf>=1.3", "h5py>=3.10", "pandas>=2.2", "requests>=2.32", "xarray>=2024.1"]
# ///
"""Ten-minute active power of the ten Delabole turbines, May 1993 to April 1994, from DTU Wind
Energy's Delabole SCADA record on DTU Data.

delabole_all.nc (16 MB) holds poa01 to poa10, active power in kW (units attribute), with a
quality flag each (0 not checked, 1 accepted, 9 defective). Traps handled: the summary says 8
turbines, but there are ten power variables, matching the site documentation, so all ten are
read; values flagged 9 are dropped. The stamps are read as UTC: the file's time units carry no
zone, but the 1994 performance report linked from DTU's site page gives the time of record as
GMT, and 27 March 1994 01:00-01:50, an hour UK clocks skipped, is present. Not stated by DTU,
and not fixed here: which 10-minute statistic poa is (values reach 495 kW on 400 kW turbines;
probably the mean), and whether a stamp opens or closes its period. Licence: the files say
CC BY NC 4.0.
"""

import io

import requests
import xarray as xr

URL = "https://ndownloader.figshare.com/files/30586935"  # delabole_all.nc

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
ds = xr.open_dataset(io.BytesIO(resp.content), engine="h5netcdf")

turbines = [f"poa{n:02d}" for n in range(1, 11)]
power = ds[turbines].to_dataframe()
flags = ds[[f"{t}_qc" for t in turbines]].to_dataframe().set_axis(turbines, axis=1)
df = (
    power.mask(flags == 9)
    .rename(columns=lambda t: "T" + t[3:])
    .rename_axis(index="time_utc", columns="unit_id")
    .stack()
    .dropna()
    .rename("power_kw")
    .reset_index("unit_id")
    .tz_localize("UTC")  # GMT per the 1994 performance report
    .sort_index()
)
print(df)
mwh = df["power_kw"].sum() / 6 / 1000  # kW x 1/6 h, if poa is a 10-minute mean
print(f"{len(df)} turbine-10-minutes over {df['unit_id'].nunique()} turbines, {mwh:.0f} MWh "
      f"(mean {df['power_kw'].mean():.0f} kW per 400 kW turbine)")
