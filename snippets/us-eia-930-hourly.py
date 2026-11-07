# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly ERCOT wind for one day from EIA's Form EIA-930 six-month bulk file (no key needed).

The bulk CSV (about 47 MB) holds every balancing authority's hourly net generation by source, as
hourly integrated MW, so each value is also the MWh in that hour. EIA's API v2 serves the same
data but needs a key; this file does not. The sample is 8 March 2026, when US clocks went
forward. Traps handled:
- stamps are hour-ending; the "UTC Time at End of Hour" column is used (the local column has
  daylight-saving gaps) and shifted back one hour to the hour start;
- since July 2024 wind is split into "with" and "without integrated battery storage"; the two
  are added;
- each value comes as reported, imputed and adjusted; the adjusted columns are chosen;
- headers carry typos and double spaces, so they are normalised before matching.
"""

import io

import pandas as pd
import requests

URL = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_2026_Jan_Jun.csv"
BA, DAY = "ERCO", "03/08/2026"  # ERCOT; "Data Date" is the balancing authority's local day

resp = requests.get(URL, timeout=180)
resp.raise_for_status()
rows = pd.read_csv(io.BytesIO(resp.content), thousands=",", low_memory=False)
rows.columns = rows.columns.str.split().str.join(" ")
rows = rows[(rows["Balancing Authority"] == BA) & (rows["Data Date"] == DAY)]

wind = [c for c in rows.columns if "from Wind" in c and c.endswith("(Adjusted)")]
end = pd.to_datetime(rows["UTC Time at End of Hour"], format="%m/%d/%Y %I:%M:%S %p", utc=True)
df = (
    rows.assign(time_utc=end - pd.Timedelta(hours=1),
                wind_mw=rows[wind].astype(float).sum(axis=1, min_count=1))
    .set_index("time_utc")
    .sort_index()[["wind_mw"]]
)
print(df)
print(f"{len(df)} hours, {df['wind_mw'].sum() / 1000:.1f} GWh")  # hourly MW = MWh
