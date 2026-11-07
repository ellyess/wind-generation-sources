# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual production of every Swiss wind facility, from the Swiss Federal Office of Energy (BFE).

The CSV package (7 kB zip) holds a production table with one total per facility and calendar
year, joined here to the facility table for its name and rated power. Traps handled: the files
give production with no unit, and the publisher's own map pop-up gives the same figures in kWh,
so they are converted from kWh to MWh (and rated power from kW to MW); facility histories have
gaps, so a year is summed only over the facilities that reported it, and the count is printed.
Not handled by code: the figures are what operators told BFE, some rounded, not metered values;
coordinates (x, y) are Swiss LV95 metres (EPSG:2056), not longitude and latitude.
"""

import io
import zipfile

import pandas as pd
import requests

URL = ("https://data.geo.admin.ch/ch.bfe.windenergieanlagen/windenergieanlagen/"
       "windenergieanlagen_2056.csv.zip")

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
    def table(name: str) -> pd.DataFrame:
        return pd.read_csv(zf.open(f"Windenergyplants_V1.{name}.csv"), encoding="utf-8-sig")
    production = table("Production.Production")
    facility = table("Plant.Facility").set_index("xtf_id")

df = (
    production.join(facility[["name", "ratedPower", "x", "y"]], on="facility")
    .assign(period=lambda d: d["year"].astype(str), wind_mwh=lambda d: d["production"] / 1e3,
            capacity_mw=lambda d: d["ratedPower"] / 1e3)
    .rename(columns={"name": "unit_id"})
    .set_index("period")
    .sort_index()[["unit_id", "wind_mwh", "capacity_mw", "x", "y"]]
)
print(df)
last = df.loc[df.index.max()]
print(f"{len(df)} facility-years; {df.index.max()}: {len(last)} facilities reporting, "
      f"{last['wind_mwh'].sum() / 1e3:.1f} GWh")
