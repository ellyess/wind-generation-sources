# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Latvian monthly gross wind generation for one year, CSB table ENB010m (PxWeb API).

Indicator WT ("..wind turbines") is gross electricity production from wind in million kWh
(GWh) per month, labelled like 2025M01, which is turned into 2025-01 here. Trap handled:
- values are whole GWh, so a small month carries a large rounding error; the printed total
  keeps that in view (each month is good to plus or minus 0.5 GWh).
"""

import pandas as pd
import requests

YEAR = 2025
URL = "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/NOZ/EN/ENB/ENB010m"
months = [f"{YEAR}M{m:02d}" for m in range(1, 13)]
query = {
    "query": [
        {"code": "INDICATOR", "selection": {"filter": "item", "values": ["WT"]}},
        {"code": "TIME", "selection": {"filter": "item", "values": months}},
    ],
    "response": {"format": "json"},
}
resp = requests.post(URL, json=query, timeout=60)
resp.raise_for_status()
js = resp.json()
assert "million. kWh" in js["columns"][-1]["text"]  # million kWh = GWh

rows = pd.DataFrame([(r["key"][1], r["values"][0]) for r in js["data"]],
                    columns=["label", "wind_gwh"])
df = (
    rows.assign(period=rows["label"].str.replace("M", "-"),
                wind_gwh=pd.to_numeric(rows["wind_gwh"], errors="coerce"))
    .set_index("period")[["wind_gwh"]]
)
print(df)
print(f"{len(df)} months, {df['wind_gwh'].sum():.0f} GWh "
      f"(rounding: +/- {0.5 * len(df):.0f} GWh at most)")
