# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "python-calamine>=0.2", "requests>=2.32"]
# ///
"""Hourly MW of Guatemala's wind units for 15 February 2026, from the "Carga Horaria" sheet of
AMM's daily post-dispatch report (Informe de Posdespacho Diario).

One zip per day holds the workbook; the sheet gives MW per generating unit, about 150 columns,
for hours labelled 1 to 24. Traps handled: the hour column mixes whole hours with extra
quarter-hour readings around the peaks written as decimals (11.3 is 11:30, 18.15 is 18:15), so
only whole-number labels are kept; unit columns move from day to day, so wind units are found
by their code suffix "-E" (SNT-E San Antonio El Sitio, VBL-E Viento Blanco, LCU-E Las Cumbres),
not by position; the daily figure in the row above hour 1 is kept apart, not read as an hour.
Not fixable in code: AMM does not say whether a value is an hourly average or a reading at the
hour, nor which clock the hours follow, so no UTC stamp is built and df is indexed by the
published hour label (Guatemala keeps UTC-6 all year). Files up to at least 2016 are .xls
inside the zip and later ones .xlsx; the calamine engine reads both.
"""

import io
import zipfile

import pandas as pd
import requests

URL = ("https://www.amm.org.gt/pdfs2/post_despacho/POSDESPACHO_DIARIO/"
       "2026/02_FEBRERO/PD20260215.zip")

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
archive = zipfile.ZipFile(io.BytesIO(resp.content))
book = io.BytesIO(archive.read(archive.namelist()[0]))
sheet = pd.read_excel(book, sheet_name="Carga Horaria", header=None, engine="calamine")

labels = pd.to_numeric(sheet[0], errors="coerce")
first_hour = labels[labels == 1].index[0]
codes = sheet.loc[first_hour - 2].astype(str).str.strip()  # unit codes, then the daily row
wind = codes[codes.str.fullmatch(r"[A-Z]{3}-E\d*")]
daily = sheet.loc[first_hour - 1, wind.index].set_axis(wind).astype(float)

hourly = sheet.loc[labels.notna() & (labels == labels.round()), [0, *wind.index]]
df = (
    hourly.set_index(0).set_axis(wind, axis=1)
    .rename_axis(index="hour", columns="unit_id")
    .rename(index=int)
    .stack()
    .astype(float)
    .rename("wind_mw")
    .reset_index("unit_id")
)
print(df)
mwh = df["wind_mw"].sum()  # MW x 1 h, if each value is an hour's mean
print(f"{len(df)} unit-hours over {df['unit_id'].nunique()} units, {mwh:.1f} MWh if hourly "
      f"means (AMM's daily row sums to {daily.sum():.1f})")
