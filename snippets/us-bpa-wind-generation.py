# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Wind generation in the BPA balancing authority for 2025, every five minutes.

BPA's yearly workbook gives five-minute MW snapshots from its control system. Traps handled:
- the file has a Pacific-time "Date/Time" column and a "Date/Time (UTC)" column; the UTC one is
  used, so daylight saving does not matter;
- only "TOTAL WIND GENERATION IN BPA CONTROL AREA" (SCADA 79687) is measured output; the wind
  "base schedule" and "basepoint" columns beside it are forecasts and dispatch targets, and are
  left out (the header has a double space, so it is matched by its SCADA point);
- values are instantaneous snapshots, so the energy line is an approximation (MW x 1/12 h).
Plants shared with other balancing areas count only BPA's share.
"""

import io

import pandas as pd
import requests

URL = ("https://transmission.bpa.gov/Business/Operations/Wind/OPITabularReports/"
       "WindGenTotalLoadYTD_2025.xlsx")

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
rows = pd.read_excel(io.BytesIO(resp.content), sheet_name="Data", header=1)
wind = next(c for c in rows.columns if "SCADA 79687" in c)

df = (
    rows.assign(time_utc=pd.to_datetime(rows["Date/Time (UTC)"], format="%m/%d/%y %H:%M",
                                        utc=True))
    .set_index("time_utc")
    .sort_index()[[wind]]
    .rename(columns={wind: "wind_mw"})
)
print(df)
print(f"{len(df)} five-minute snapshots, {df['wind_mw'].sum() / 12 / 1e6:.2f} TWh (approx.)")
