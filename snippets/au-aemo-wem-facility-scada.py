# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Five-minute SCADA energy for every Western Australian wind farm, for one month (post-reform).

From 1 October 2023 the WEM facility SCADA CSV gives "Average MWh": the energy measured in each
five-minute dispatch interval, stamped at the interval start, in Western Australian time.
Traps handled: stamps are day-first ("01/10/2026 07:55:00"), although the field definition says
YYYY-MM-DD, so the format is given explicitly; they are read as a fixed UTC+08:00, not as
Australia/Perth; MWh per five minutes is converted to average MW (x 12). The file runs by
trading day (08:00 to 08:00), newest row first, and is sorted here. Facility codes carry no fuel
type: wind farms are picked by their code ("_WF" plus a number, or ALINTA_WWF), and the system
size comes from post-facilities/facilities.csv. Not covered: the pre-reform 30-minute files.
"""

import io

import pandas as pd
import requests

MONTH = "2026-09"
DATA = "https://data.wa.aemo.com.au/public/public-data/datafiles"


def csv(path: str) -> pd.DataFrame:
    resp = requests.get(f"{DATA}/{path}", timeout=120)
    resp.raise_for_status()
    return pd.read_csv(io.BytesIO(resp.content), low_memory=False)


rows = csv(f"facility-scada-csv/FacilityScada-{MONTH}.csv")
rows = rows[rows["Facility Code"].str.contains(r"_WF\d+$|_WWF$")]
size = csv("post-facilities/facilities.csv").set_index("Facility Code")["System Size (MW)"]

local = pd.to_datetime(rows["Dispatch Interval"], format="%d/%m/%Y %H:%M:%S")
df = (
    rows.assign(time_utc=local.dt.tz_localize("Etc/GMT-8").dt.tz_convert("UTC"),
                wind_mwh=rows["Average MWh"], wind_mw=rows["Average MWh"] * 12)
    .rename(columns={"Facility Code": "unit_id"})
    .set_index("time_utc")
    .sort_index()[["unit_id", "wind_mwh", "wind_mw"]]
)
print(df)
fleet = size.reindex(df["unit_id"].unique()).sum()
print(f"{len(df)} intervals, {df['unit_id'].nunique()} wind farms ({fleet:.0f} MW), "
      f"{df['wind_mwh'].sum() / 1e3:.1f} GWh")
