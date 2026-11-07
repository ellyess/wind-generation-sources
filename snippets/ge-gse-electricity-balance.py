# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Monthly wind generation in Georgia for 2025 from the Georgian State Electrosystem's actual
electricity balance, a one-page PDF per year.

The year's PDF link comes from the JSON listing that GSE's own page loads (an undocumented but
public endpoint). Values are monthly totals in million kWh, which is GWh. Traps handled: numbers
use a space for thousands and a comma for decimals in recent files ("1 102,67") but a point for
decimals in 2016 ("1.835"), so spaces are stripped and a comma becomes a point, which reads both
correctly; from 2026 the file lists each wind farm (Qartli, Zemo, Ruisi) under the "Wind Power
Plants" subtotal, whose cells merge when extracted, so the farm rows are kept and the subtotal
dropped whenever farm rows exist. In 2025 Qartli was the only farm, so only the subtotal exists.
"""

import io

import pandas as pd
import pdfplumber
import requests

YEAR = "2025"

listing = requests.get("https://admin.gse.com.ge/api/en/menu/actual-balance-125", timeout=60)
listing.raise_for_status()
files = {f["name"]: f["path"] for c in listing.json()["data"]["contents"] for f in c["files"]}
pdf = requests.get(files[YEAR], timeout=60)
pdf.raise_for_status()
table = pdfplumber.open(io.BytesIO(pdf.content)).pages[0].extract_tables()[0]

months, rows = table[0][1:13], [r for r in table if r[0] and "Wind" in r[0]]
if any("Wind Farm" in r[0] for r in rows):
    rows = [r for r in rows if "Wind Farm" in r[0]]
wide = pd.DataFrame([r[1:13] for r in rows], index=[r[0] for r in rows], columns=months)

df = (
    wide.T.set_axis(pd.period_range(f"{YEAR}-01", periods=12, freq="M"), axis=0)
    .rename_axis(index="period", columns="unit_id")
    .stack()
    .str.replace(" ", "").str.replace(",", ".")
    .replace("", None)
    .dropna()
    .astype(float)
    .rename("wind_gwh")
    .reset_index("unit_id")
)
print(df)
print(f"{len(df)} plant-months, {df['wind_gwh'].sum():.1f} GWh")
