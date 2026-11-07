# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Monthly net wind generation per US plant for 2024 from EIA's Form EIA-923 bulk file.

The yearly zip (about 23 MB, no key) holds "Netgen January" to "Netgen December" in MWh per
plant, prime mover and fuel. Wind is fuel code WND. Traps handled:
- plants that report once a year with an annual total only ("Respondent Frequency" A) have
  months filled in by EIA. From 2023 wind's annual respondents are coded AM instead: they
  report each month, once a year. M and AM are kept and A is dropped, so the monthly shape is
  reported, not imputed;
- plant code 99999 holds state-level increments that join to no plant, and is dropped;
- Alaska and Hawaii are dropped, to stay inside a contiguous-US weather domain;
- missing months are written ".", read here as missing.
Values are net of station use. Coordinates and nameplate are in EIA-860, joined on unit_id.
"""

import io
import zipfile

import pandas as pd
import requests

URL = "https://www.eia.gov/electricity/data/eia923/archive/xls/f923_2024.zip"
SHEET = "EIA923_Schedules_2_3_4_5_M_12_2024_Final.xlsx"

resp = requests.get(URL, timeout=180)
resp.raise_for_status()
book = zipfile.ZipFile(io.BytesIO(resp.content)).open(SHEET)
rows = pd.read_excel(book, sheet_name="Page 1 Generation and Fuel Data", header=5)
rows.columns = rows.columns.str.replace("\n", " ")
rows = rows[(rows["Reported Fuel Type Code"] == "WND")
            & rows["Respondent Frequency"].isin(["M", "AM"])
            & (rows["Plant Id"] != 99999) & ~rows["Plant State"].isin(["AK", "HI"])]

months = [c for c in rows.columns if c.startswith("Netgen ")]
long = rows.melt(id_vars=["Plant Id"], value_vars=months, var_name="month", value_name="mwh")
long["period"] = pd.to_datetime("2024 " + long["month"].str[7:], format="%Y %B").dt.strftime(
    "%Y-%m")
long["wind_mwh"] = pd.to_numeric(long["mwh"], errors="coerce")
df = (
    long.rename(columns={"Plant Id": "unit_id"})
    .groupby(["period", "unit_id"])["wind_mwh"].sum(min_count=1)  # adds WT and WS rows
    .reset_index("unit_id")
)
print(df)
print(f"{len(df)} plant-months from {df['unit_id'].nunique()} plants reporting monthly values, "
      f"{df['wind_mwh'].sum() / 1e6:.1f} TWh")
