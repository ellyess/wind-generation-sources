# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32", "openpyxl>=3.1"]
# ///
"""Monthly net wind production in Bulgaria, from the National Statistical Institute (NSI).

The workbook's "2024-2026" sheet has one column per month, with the year on one header row and
the Roman-numeral month on the next, and one row per item in GWh. The snippet takes the
"of which Wind" row and turns the two header rows into a period. Traps handled:
- months before January 2026 are "x" (not applicable: no fuel split was published) and are
  dropped rather than read as zero;
- the year label appears only above January, so it is carried forward across the months;
- wind is part of net production (gross minus the station's own needs); the check below confirms
  the products add up to net production for January 2026.
"""

import io

import pandas as pd
import requests

URL = ("https://www.nsi.bg/sites/default/files/files/data/timeseries/"
       "Energy-1.4.Electricity_en.xlsx")
ROMAN = {r: i for i, r in enumerate("I II III IV V VI VII VIII IX X XI XII".split(), 1)}

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
sheet = pd.read_excel(io.BytesIO(resp.content), sheet_name="2024-2026", header=None)
label = sheet[0].astype(str).str.strip()
years = sheet.iloc[3, 2:].ffill().astype(int)
months = sheet.iloc[4, 2:].map(ROMAN)
periods = [f"{y}-{m:02d}" for y, m in zip(years, months, strict=True)]

def row(name):
    values = sheet.loc[label == name].iloc[0, 2:]
    return pd.to_numeric(values.set_axis(periods), errors="coerce")

assert (sheet.loc[label == "of which Wind", 1] == "GWh").all()
df = row("of which Wind").dropna().rename("wind_gwh").rename_axis("period").to_frame()
jan = pd.to_numeric(sheet.loc[label.str.startswith("of which"), periods.index("2026-01") + 2])
assert abs(jan.sum() - row("Net production")["2026-01"]) <= 5, "products do not sum to net"
print(df)
print(f"{len(df)} months, {df['wind_gwh'].sum():,.0f} GWh net wind production")
