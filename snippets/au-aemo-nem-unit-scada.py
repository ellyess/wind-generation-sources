# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Five-minute SCADA readings for every wind unit in Australia's NEM, for one month (MMSDM).

DISPATCH_UNIT_SCADA gives one instantaneous MW reading per dispatch unit (DUID), taken at the
start of each five-minute interval but stamped with the interval's end, in NEM time (fixed
UTC+10:00, no daylight saving). Traps handled: stamps are moved back five minutes, so each row
sits at the moment of its reading; NEM time is converted to UTC as a fixed offset, not as
Australia/Sydney; the month archive is cut on NEM-time month boundaries, so in UTC it starts at
14:00 on the last day of the previous month. DUIDs carry no fuel type: wind units are picked
with the same month's GENUNITS register (CO2E_ENERGY_SOURCE "Wind") mapped to DUIDs by DUALLOC.
The values are readings, so MW x 5/60 h only estimates energy. The SCADA zip is about 33 MB.
"""

import io
import zipfile

import pandas as pd
import requests

MONTH = "2026_09"
BASE = (f"https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/{MONTH[:4]}/MMSDM_{MONTH}"
        f"/MMSDM_Historical_Data_SQLLoader/DATA/PUBLIC_ARCHIVE%23{{}}%23FILE01%23"
        f"{MONTH.replace('_', '')}010000.zip")


def table(name: str, usecols: list[int]) -> pd.DataFrame:
    resp = requests.get(BASE.format(name), timeout=300)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        raw = pd.read_csv(zf.open(zf.namelist()[0]), header=None, usecols=[0, *usecols],
                          skiprows=1, low_memory=False)
    head = raw[raw[0] == "I"].iloc[0, 1:].tolist()  # the column names, from the "I" row
    return raw[raw[0] == "D"].iloc[:, 1:].set_axis(head, axis=1)


gen = table("GENUNITS", [4, 21])  # GENSETID, CO2E_ENERGY_SOURCE
wind_sets = set(gen.loc[gen["CO2E_ENERGY_SOURCE"] == "Wind", "GENSETID"])
alloc = table("DUALLOC", [6, 7])  # DUID, GENSETID
wind_duids = set(alloc.loc[alloc["GENSETID"].isin(wind_sets), "DUID"])

scada = table("DISPATCH_UNIT_SCADA", [4, 5, 6])  # SETTLEMENTDATE, DUID, SCADAVALUE
scada = scada[scada["DUID"].isin(wind_duids)]
nem_time = pd.to_datetime(scada["SETTLEMENTDATE"], format="%Y/%m/%d %H:%M:%S")
df = (
    scada.assign(time_utc=(nem_time - pd.Timedelta(minutes=5)).dt.tz_localize("Etc/GMT-10")
                 .dt.tz_convert("UTC"),
                 wind_mw=pd.to_numeric(scada["SCADAVALUE"]))
    .rename(columns={"DUID": "unit_id"})
    .set_index("time_utc")
    .sort_index()[["unit_id", "wind_mw"]]
)
print(df)
print(f"{len(df)} readings, {df['unit_id'].nunique()} wind units, "
      f"~{df['wind_mw'].sum() * 5 / 60 / 1e3:.0f} GWh estimated (MW x 5/60 h)")
