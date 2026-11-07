# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32", "openpyxl>=3.1"]
# ///
"""Indian wind generation by state for one day, from CEA's Daily Renewable Generation Report.

The "Generation" sheet gives the all-India total by state, net, in million units (MU, that is
GWh) for the report day and the month to date. CEA does not say which time zone defines the
day, so rows are labelled with the report date as `period` rather than a UTC stamp. Traps
handled:
- sheet order changes between workbooks, so the sheet is read by name, not position;
- regional subtotals and the all-India row sit among the states; they are separated so the
  states are not counted twice, and the state sum is checked against the all-India row.
"""

import io

import pandas as pd
import requests

DAY = "2026-11-05"

resp = requests.get(
    f"https://gen-re.cea.gov.in/renewables/public/uploads/dailyReport/excel/Report-{DAY}.xlsx",
    timeout=60,
)
resp.raise_for_status()
sheet = pd.read_excel(io.BytesIO(resp.content), sheet_name="Generation", header=None)
assert "Figures in MU net" in str(sheet.iloc[3, 5])  # MU = GWh

rows = sheet.iloc[6:, [0, 1]].dropna(subset=[0]).set_axis(["label", "wind_gwh"], axis=1)
rows["area"] = rows["label"].str.split("/").str[-1].str.strip()  # English half of the label
is_total = rows["area"].str.contains("Region|All India")
all_india = rows.loc[rows["area"].eq("All India"), "wind_gwh"].item()

df = (
    rows[~is_total]
    .assign(period=DAY, wind_gwh=lambda d: d["wind_gwh"].astype(float))
    .set_index("period")[["area", "wind_gwh"]]
)
print(df)
print(f"{len(df)} states, {df['wind_gwh'].sum():.2f} GWh (all-India row: {all_india} GWh)")
