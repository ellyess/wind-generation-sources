# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Mauritius monthly wind generation (kWh) from Statistics Mauritius, January 2013 onwards.

One xlsx sheet with one row per energy source and one column per month; values are kWh
generated in the month. Traps handled:
- months are columns, so the Wind row is picked out and turned into a monthly series;
- the last column is a percentage change (-0.97 for wind), not kWh, so only columns whose
  header is a month are kept;
- "-" means not applicable before a source existed, read as missing.
The file name changes with each release (this one holds data to August 2026, released
6 November 2026); take the current link from the Energy and Water subject page. Recent months
are revised, so re-download rather than append.
"""

import io

import pandas as pd
import requests

URL = ("https://statsmauritius.govmu.org/Documents/Statistics/By_Subject/Energy_Water/"
       "Electricity/Electricity_Generation_M_Aug26_061126.xlsx")

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
sheet = pd.read_excel(io.BytesIO(resp.content), header=None)

header = sheet.iloc[2]  # the "Month / Year" row: dates, then a "% Change" label
wind = sheet[sheet[0].astype(str).str.strip() == "Wind"].iloc[0]
months = [c for c in sheet.columns if hasattr(header[c], "year")]  # month columns only

df = pd.DataFrame({
    "period": [header[c].strftime("%Y-%m") for c in months],
    "wind_kwh": pd.to_numeric(wind[months], errors="coerce").to_numpy(),  # "-" -> NaN
}).set_index("period")
print(df)
print(f"{len(df)} months, {df['wind_kwh'].sum() / 1e6:.1f} GWh")  # kWh / 1e6
