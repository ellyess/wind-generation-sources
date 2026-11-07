# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Monthly energy per Argentine wind farm from CAMMESA's renewables database (one ZIP, ~2 MB).

The workbook gives energy generated in GWh per plant and machine for each month since January
2011, labelled by month. This reads the September 2026 release, at the dated address that the
page's download link redirects to (earlier releases stay at their own dated addresses).

Traps handled:
- The summary sheet "Tabla Resumen x Central" has its header on row 5 and merged region and
  province cells; this reads the long sheet "Base de Datos" instead, which has one plain row per
  machine and month, so nothing needs forward-filling.
- Some plants appear under two names (ARAUEO is both "PARQUE EOLICO ARAUCO SAPEM" and "ARAUCO
  EOLICO"), so rows are grouped by plant code, not name; codes with no output at all are dropped.
- There is no capacity in the file, so no capacity factor is computed here.
"""

import io
import zipfile

import pandas as pd
import requests

URL = ("https://microfe.cammesa.com/static-content/CammesaWeb/download-manager-files/"
       "historica%20renovables/Energ%c3%ada%20Renovables%20-%20Base%20de%20Datos%202026-09.zip")

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
    rows = pd.read_excel(z.open(z.namelist()[0]), sheet_name="Base de Datos", header=1)

wind = rows[rows["FUENTE DE ENERGÍA"] == "EOLICO"]
df = (
    wind.assign(period=wind["MES"].dt.strftime("%Y-%m"))
    .groupby(["period", "CENTRAL"], as_index=False)
    .agg(name=("CENTRAL DESCRIPCIÓN", "last"), province=("PROVINCIA", "first"),
         wind_gwh=("ENERGÍA GENERADA [GWh]", "sum"))
    .rename(columns={"CENTRAL": "unit_id"})
)
df = df[df.groupby("unit_id")["wind_gwh"].transform("sum") > 0].set_index("period")
print(df)
last = df.loc[df.index.max()]
print(f"{len(df)} plant-months, {df['unit_id'].nunique()} plants, {df['wind_gwh'].sum():.0f} GWh "
      f"since 2011; {df.index.max()}: {len(last)} plants, {last['wind_gwh'].sum():.0f} GWh")
