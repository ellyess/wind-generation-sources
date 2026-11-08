# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "python-calamine>=0.2", "requests>=2.32"]
# ///
"""Hourly post-dispatch power per Dominican wind plant for one day from OC-SENI's daily report.

Downloads one zipped workbook (1 October 2026, version V0) from the shared Dropbox folder the OC
page links to (dl=1 fetches the file) and reads the PostDespacho sheet: MW for periods 1 to 24
per unit, and a daily (MWH) column equal to their sum. Traps handled: wind rows are picked by
code or by "EÓLICO"/"EOLICO" in the name, not by plant name, because solar plants share the
Esperanza name; Los Cocos 1 and 2 and Quilvio Cabrera have no "eólico" in their names, so their
codes are listed. Small negative values (auxiliary use) are kept. Not handled: the publisher
does not state the zone, which hour period 1 covers, or mean versus snapshot; here period p is
placed at p-1:00 on the report day as a naive `time` (the `period` column keeps the label), not
converted to UTC; Dominican time is UTC-4 all year, but the zone is not stated. Check the
month folder for a later version (V1) of a day; the folder only lists with JavaScript.
"""

import io
import zipfile

import pandas as pd
import requests

URL = ("https://www.dropbox.com/scl/fo/nhabegwb8jkh28wvxh7h8/ANIK6_G2ZIjRKl99E32bAmI/"
       "01.%20Informe%20Diario%20de%20Operacion/2026/10.%20Octubre/"
       "Informe%20Diario%20OC-01-10-26-V0.zip?rlkey=w6dtkv2m3ss8ov7922top7256&dl=1")
DAY = "2026-10-01"
NO_EOLICO_IN_NAME = {"G3JCOCO1", "G3LCOCO2", "G3QCABRE"}  # Los Cocos 1, 2, Quilvio Cabrera

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
    xls = z.read(z.namelist()[0])
raw = pd.read_excel(io.BytesIO(xls), sheet_name="PostDespacho", header=None, engine="calamine")
assert "Postdespacho [MW]" in str(raw.iloc[2, 1])

units = raw.iloc[:, 1:28].dropna(subset=[3])  # unit rows have a value for period 1
units.columns = ["code", "name", *range(1, 25), "daily_mwh"]
is_wind = units["name"].str.contains("E[OÓ]LIC", regex=True) & units["code"].str.startswith("G3")
wind = units[is_wind | units["code"].isin(NO_EOLICO_IN_NAME)]

long = wind.melt(id_vars=["code", "name"], value_vars=list(range(1, 25)),
                 var_name="period", value_name="wind_mw")
start = pd.Timestamp(DAY)  # the zone is not stated, so no UTC conversion
df = (
    long.assign(time=start + pd.to_timedelta(long["period"] - 1, unit="h"),
                wind_mw=long["wind_mw"].astype(float))
    .rename(columns={"code": "unit_id"})
    .set_index("time")
    .sort_index()[["unit_id", "name", "period", "wind_mw"]]
)
print(df)
print(f"{len(df)} plant-hours, {df['unit_id'].nunique()} wind plants, "
      f"{df['wind_mw'].sum():.1f} MWh (MW x 1 h)")
