# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Senegal annual wind energy (GWh) and capacity (MW) from Senelec's 2024 annual report (PDF).

Senegal has one grid wind farm, Taïba Ndiaye (158.7 MW), so the "Eolien" row is both the farm
and the national total. Two tables are read: production by energy source (GWh, 2023 and 2024)
and installed capacity by source (MW, 2022 to 2024). Traps handled:
- numbers are French-formatted ("1 737,97"): spaces group thousands and a comma is the decimal
  point;
- the report has several tables with an "Eolien" row, so each is found by its header.
Not handled: the 2020 report gives two different figures for 2020 (217.39 GWh in the purchases
table, 178.58 GWh by source); only the 2024 report is read here.
"""

import io

import pandas as pd
import pdfplumber
import requests

URL = "https://www.senelec.sn/media/rapports/pdf/rapport-annuel-senelec-20241760024319_1.pdf"


def number(text):
    return float(text.replace(" ", "").replace(" ", "").replace(",", "."))


resp = requests.get(URL, timeout=120)
resp.raise_for_status()
found = {}
with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
    for page in pdf.pages:
        for table in page.extract_tables():
            head = table[0]
            for name, title in [("wind_gwh", "Production par Sources"),
                                ("capacity_mw", "Puissances Installées (MW)")]:
                if name not in found and head[0] and head[0].startswith(title):
                    wind = next(r for r in table if r[0] == "Eolien")
                    years = [h for h in head if h and h.isdigit()]
                    values = wind[1:len(years) + 1]
                    found[name] = {y: number(v) for y, v in zip(years, values, strict=True)}

df = pd.DataFrame(found).rename_axis("period").sort_index()
print(df)
print(f"{len(df)} years, {df['wind_gwh'].sum():,.2f} GWh in the years with production")
