# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32", "truststore>=0.10"]
# ///
"""Sweden annual wind production (GWh) and year-end capacity (MW), onshore and offshore, 2003 on.

Swedish Energy Agency table EN0105_5, through its PxWeb API (one JSON POST). Annual totals only:
use them as a denominator and an audit, not as a time series. Traps handled:
- the table holds a third installation type, "Supplementary source, not distributed",
  populated for 2025 only (524 GWh, no capacity), kept as its own column so it is neither lost
  nor mixed into onshore;
- cells are text, with "." and ".." for no data, read as missing, not zero;
- the server does not send its intermediate certificate, so the default certifi bundle fails;
  truststore uses the operating system's verifier, which fetches it (macOS and Windows; on
  Linux the request may still fail). Verification stays on.
"""

import pandas as pd
import requests
import truststore

truststore.inject_into_ssl()

URL = ("https://pxexternal.energimyndigheten.se/api/v1/en/Energimyndighetens_statistikdatabas/"
       "Officiell_energistatistik/Vindkraftsstatistik/EN0105_5.px")
meta = requests.get(URL, timeout=60).json()
years = next(v for v in meta["variables"] if v["code"] == "År")
labels = dict(zip(years["values"], years["valueTexts"], strict=True))

resp = requests.post(URL, json={
    "query": [{"code": "Kategori", "selection": {"filter": "item", "values": ["1", "2"]}}],
    "response": {"format": "json"}}, timeout=60)
resp.raise_for_status()
rows = pd.DataFrame([r["key"] + r["values"] for r in resp.json()["data"]],
                    columns=["year", "type", "category", "value"])

rows["period"] = rows["year"].map(labels)
rows["type"] = rows["type"].map({"0": "offshore", "1": "onshore", "2": "supplementary"})
rows["column"] = rows["type"] + rows["category"].map({"1": "_capacity_mw", "2": "_gwh"})
df = (
    rows.assign(value=pd.to_numeric(rows["value"], errors="coerce"))  # "." and ".." -> NaN
    .pivot(index="period", columns="column", values="value")
    .rename_axis(columns=None)[["onshore_gwh", "offshore_gwh", "supplementary_gwh",
                                "onshore_capacity_mw", "offshore_capacity_mw"]]
)
pd.set_option("display.max_columns", None, "display.width", 140)
print(df)
latest = df.iloc[-1]
energy = latest["onshore_gwh"] + latest["offshore_gwh"]
capacity = latest["onshore_capacity_mw"] + latest["offshore_capacity_mw"]
print(f"{len(df)} years; {df.index[-1]}: {energy:,.0f} GWh onshore and offshore, "
      f"{capacity:,.0f} MW")
