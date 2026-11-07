# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual onshore and offshore wind generation and capacity by country from IRENASTAT (no key).

IRENA's PxWeb API answers a JSON query (POST) with generation in GWh and installed capacity in
MW per country, technology and year. Traps handled:
- the table name changes with each half-yearly release, so the current Country_ELECSTAT table is
  found by listing the folder;
- generation is gross and includes off-grid output; grid connection "All" is asked for
  explicitly;
- the latest generation year is preliminary and later years are empty; empty cells stay missing;
- some country values are wrong (South Africa's onshore 2022-2024 is about 30 times too low), so
  an implied capacity factor is added: values far below about 0.15 deserve a second source.
Capacity is end of year, so the capacity factor is rough in years of fast growth.
"""

import pandas as pd
import requests

API = "https://pxweb.irena.org/api/v1/en/IRENASTAT/Power%20Capacity%20and%20Generation/"

tables = requests.get(API, timeout=60).json()
table = next(t["id"] for t in tables if t["id"].startswith("Country_ELECSTAT"))
meta = {v["code"]: v for v in requests.get(API + table, timeout=60).json()["variables"]}


def codes(var, texts):
    v = meta[var]
    return [c for c, t in zip(v["values"], v["valueTexts"], strict=True) if t in texts]


query = [{"code": var, "selection": {"filter": "item", "values": vals}} for var, vals in [
    ("Technology", codes("Technology", {"Onshore wind energy", "Offshore wind energy"})),
    ("Data Type", meta["Data Type"]["values"]),
    ("Grid connection", codes("Grid connection", {"All"}))]]
resp = requests.post(API + table, json={"query": query, "response": {"format": "json-stat2"}},
                     timeout=120)
resp.raise_for_status()
js = resp.json()

dims = [pd.Index([js["dimension"][d]["category"]["label"][k] if d != "Country/area" else k
                  for k in js["dimension"][d]["category"]["index"]], name=d) for d in js["id"]]
cells = pd.Series(js["value"], index=pd.MultiIndex.from_product(dims), dtype=float)
wide = cells.droplevel("Grid connection").unstack("Data Type")
df = (
    wide.rename(columns={"Electricity Generation (GWh)": "wind_gwh",
                         "Electrical Installed Capacity (MW)": "capacity_mw"})
    .reset_index().rename(columns={"Country/area": "country", "Technology": "technology",
                                   "Year": "period"})
    .dropna(subset=["wind_gwh", "capacity_mw"], how="all")
    .set_index("period").sort_index()
)
df["capacity_factor"] = df["wind_gwh"] * 1000 / (df["capacity_mw"] * 8760)
print(df)
print(f"{len(df)} country-technology-years; 2024: {df.loc['2024', 'wind_gwh'].sum() / 1000:.0f} TWh"
      f" from {df.loc['2024', 'capacity_mw'].sum() / 1000:.0f} GW")
