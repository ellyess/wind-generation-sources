# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Peru daily wind energy per plant (MWh) for one day from COES's generation Excel export.

The export (ExportarGeneracion, the call behind the portal's Excel button; undocumented) has a
sheet "PRODUCCIÓN DIARIA" with one row per plant and day. Traps handled:
- the portal's JSON call is keyed by company with empty plant fields, so the Excel export is
  used instead and keyed on the plant column (GRUPO/CENTRAL), not the company, whose name changes;
- farms split into blocks or extensions (Punta Lomitas BL1/BL2 and its _EXP blocks, Wayra-I and
  Wayra Extension) get a farm column so they can be added up;
- indicador=1 picks the 15-minute meter data, which fill in during the first days of the next
  month; indicador=0 gives the SCADA figures, which differ slightly.
COES does not say which clock defines the day, so the day stays a label (period), not a UTC time.
"""

import io

import pandas as pd
import requests

DAY = pd.Timestamp("2026-10-01")

resp = requests.get(
    "https://www.coes.org.pe/Portal/portalinformacion/ExportarGeneracion",
    params={"fechaInicial": DAY.strftime("%d/%m/%Y"), "fechaFinal": DAY.strftime("%d/%m/%Y"),
            "indicador": 1},
    timeout=60,
)
resp.raise_for_status()
rows = pd.read_excel(io.BytesIO(resp.content), sheet_name="PRODUCCIÓN DIARIA", header=3)
rows = rows[rows["TIPO GENERACIÓN"] == "EÓLICA"]

plant = rows["GRUPO/CENTRAL"].str.strip()
farm = plant.str.replace(r"^PUN(TA)? LOMITAS.*", "PUNTA LOMITAS", regex=True)
farm = farm.str.replace(r"^WAYRA.*", "WAYRA", regex=True)
df = pd.DataFrame({
    "period": pd.to_datetime(rows["FECHA"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d"),
    "unit_id": plant, "farm": farm, "wind_mwh": rows["TOTAL"],
}).set_index("period")
print(df)
print(f"{len(df)} plant-days, {df['farm'].nunique()} farms, {df['wind_mwh'].sum():,.0f} MWh")
