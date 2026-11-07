# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Curaçao's annual wind energy intake from Aqualectra's 2025 annual report (key figures page).

Reads the line "Electricity intake from wind farms in MWh" from the key figures table (PDF page
14), whose columns are Dec 31, 2025 and Dec 31, 2024. The figure is wind energy the utility
bought from the wind farm operators, not output at the turbines. Traps handled: the 2024 column
repeats the 2021 figures (196,955 MWh), so 2024 is set to missing and only the printed value is
kept; thousands are written with commas. Other years come from other reports, and not every
report has the row.
"""

import io
import re

import pandas as pd
import pdfplumber
import requests

URL = "https://www.aqualectra.com/wp-content/uploads/2026/05/4999_AQ_Annual-Report_2025_DIGI.pdf"
PAGE = 14

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
    text = pdf.pages[PAGE - 1].extract_text()
assert "Dec 31, 2025 Dec 31, 2024" in text
line = re.search(r"Electricity intake from wind farms in MWh ([\d,]+) ([\d,]+)", text)
printed = [float(v.replace(",", "")) for v in line.groups()]  # 2025, 2024

df = pd.DataFrame(
    {"printed_mwh": printed, "wind_mwh": [printed[0], float("nan")]},  # 2024 repeats 2021
    index=pd.Index(["2025", "2024"], name="period"),
)
print(df)
print(f"{df['wind_mwh'].count()} usable year, "
      f"{df['wind_mwh'].sum():,.0f} MWh bought from wind farms")
