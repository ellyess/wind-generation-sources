# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""New England daily metered wind energy for 2022 from ISO-NE's Daily Generation by Fuel Type.

The yearly workbook's DAYGENBYFUEL sheet has one row per DATE and a WIND column in MWh. The
snippet uses the workbook's direct link; the report page itself asks for a captcha, and the
month folder in the path varies by year, so each year's link must be read off that page.
Traps handled:
- each row is one day's total in MWh, although the README tab says "during the week"; nothing
  is divided by seven;
- this is the metered daily report, not the five-minute "Dispatch Fuel Mix", which is a
  dispatch-software forecast.
ISO-NE does not say which clock defines the day, so rows are labelled by DATE as a "period"
(YYYY-MM-DD), not converted to UTC. Whether offshore wind is in WIND is not stated.
"""

import io

import pandas as pd
import requests

URL = "https://www.iso-ne.com/static-assets/documents/2022/01/2022_daygenbyfuel.xlsx"

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
rows = pd.read_excel(io.BytesIO(resp.content), sheet_name="DAYGENBYFUEL")

df = (
    rows.assign(period=pd.to_datetime(rows["DATE"]).dt.strftime("%Y-%m-%d"))
    .set_index("period")
    .sort_index()[["WIND"]]
    .rename(columns={"WIND": "wind_mwh"})
)
print(df)
print(f"{len(df)} days, {df['wind_mwh'].sum() / 1000:.0f} GWh")
