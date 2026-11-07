# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Czech monthly wind production, Q2 2026, from the Energy Regulatory Office's quarterly report.

Reads sheet 4.4 of the report's XLSX edition (eruelektroq22026.xlsx): for wind (VTE), per month,
installed capacity [MWe], gross production, own consumption (TVSe), net production and delivery
to the grid, all in [MWh]. The row under "Větrné (VTE)" holds the three months; the row beside
the label holds quarter totals and is not used. Traps handled: gross and net are kept apart
(ČEPS's series is gross). Not handled in code: small unlicensed plants are computed from
capacity, unregistered plants above 100 kW are left out, and a quarter's figures are revised
in the annual report.
"""

import io

import pandas as pd
import requests

URL = "https://eru.gov.cz/sites/default/files/obsah/prilohy/eruelektroq22026.xlsx"
PERIODS = ["2026-04", "2026-05", "2026-06"]  # Duben, Květen, Červen

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
raw = pd.read_excel(io.BytesIO(resp.content), sheet_name="4.4", header=None)

label = raw.index[raw[0].astype(str).str.startswith("Větrné (VTE)")][0]
units = raw.loc[label - 2].dropna().tolist()
assert units == ["[MWe]", "[MWh]", "[MWh]", "[MWh]", "[MWh]"], units
months = raw.loc[label + 1, 1:15].astype(float).to_numpy().reshape(5, 3).T  # 5 blocks x 3 months

df = pd.DataFrame(
    months,
    index=pd.Index(PERIODS, name="period"),
    columns=["capacity_mw", "gross_wind_mwh", "own_use_mwh", "net_wind_mwh", "delivered_mwh"],
)
print(df)
print(f"{len(df)} months, {df['gross_wind_mwh'].sum() / 1000:.1f} GWh gross wind")
