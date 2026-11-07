# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly output per Bolivian wind farm for one day, from CNDC's realised dispatch workbook.

The "POST" sheet ("DESPACHO DE CARGA REALIZADO (MW)") has one row per plant and hour columns
01:00 to 24:00. Traps handled:
- each value is an instantaneous SCADA reading in MW taken on the hour, not hourly energy, so
  df is indexed by the reading's instant and the day's energy is only approximated;
- the TOTAL column is not the sum of the hours and has no stated unit, so it is not used;
- file paths change format over the years, so the file is found through CNDC's public
  WordPress listing service (an undocumented endpoint the statistics page calls);
- wind rows are the block above "SUBTOTAL EOLICO", whose plants change over the years.
The file states no time zone. This snippet assumes Bolivian clock time, UTC-04:00 all year
(Bolivia keeps no daylight saving), and reads 24:00 as midnight ending the day.
"""

import io

import pandas as pd
import requests

DAY = "2026-11-05"

listing = requests.get(
    "https://www.cndc.bo/wp-json/cndc/v1/estadisticas/documentos",
    params={"categoria_id": 270, "agrupado": "true", "anio": DAY[:4]}, timeout=60)
listing.raise_for_status()
url = next(doc["archivo_url"] for g in listing.json()["grupos"] if g["periodo"] == DAY
           for doc in g["docs"])
resp = requests.get(url, timeout=60)
resp.raise_for_status()
sheet = pd.read_excel(io.BytesIO(resp.content), sheet_name="POST", header=None)

labels = sheet[0].astype(str).str.strip()
end = labels[labels == "SUBTOTAL EOLICO"].index[0]
start = labels[:end][sheet[0][:end].isna()].index[-1] + 1  # first row after the blank line
wind = sheet.loc[start:end - 1, :24].set_index(0)
wind.columns = pd.Timestamp(DAY) + pd.to_timedelta(range(1, 25), unit="h")

df = (
    wind.stack().rename("wind_mw").rename_axis(["unit_id", "time_local"]).reset_index()
    .assign(time_utc=lambda d: d["time_local"].dt.tz_localize("-04:00").dt.tz_convert("UTC"))
    .set_index("time_utc").sort_index()[["unit_id", "wind_mw"]]
)
df["wind_mw"] = df["wind_mw"].astype(float)
print(df)
print(f"{len(df)} readings, {df['unit_id'].nunique()} farms, about "
      f"{df['wind_mw'].sum():.0f} MWh (readings x 1 h, an approximation)")
