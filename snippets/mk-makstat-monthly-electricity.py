# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""North Macedonia monthly gross wind generation for one year, MakStat (PxWeb API).

Indicator 8 ("..Wind power plants", gross production) of the table "Electricity in MWh, by
months", in MWh. Traps handled:
- the API's time codes are positions, and seven English labels are malformed ("2019_09",
  "2023_09", and "2026М01" with a Cyrillic letter, among others), so periods are built from
  the position, not the label;
- months from 2022 on are flagged preliminary, so the figures may still be revised.
"""

import pandas as pd
import requests

YEAR = 2025
URL = ("https://makstat.stat.gov.mk/PXWeb/api/v1/en/MakStat/Energija/MesecEnergetStatistiki/"
       "125_Ene_Mk_EEmes_ml.px")
FIRST = pd.Period("2012-01", "M")  # position 0 in the time variable

meta = requests.get(URL, timeout=60).json()
ind, tid = meta["variables"][0], meta["variables"][1]
assert ind["valueTexts"][8] == "..Wind power plants"
codes = [c for c in tid["values"] if (FIRST + int(c)).year == YEAR]
query = {"query": [{"code": ind["code"], "selection": {"filter": "item", "values": ["8"]}},
                   {"code": tid["code"], "selection": {"filter": "item", "values": codes}}],
         "response": {"format": "json"}}
resp = requests.post(URL, json=query, timeout=60)
resp.raise_for_status()
js = resp.json()
assert "MWh" in js["columns"][-1]["text"]

rows = pd.DataFrame([(r["key"][1], r["values"][0]) for r in js["data"]], columns=["pos", "v"])
df = (
    rows.assign(period=[str(FIRST + int(p)) for p in rows["pos"]],
                wind_mwh=pd.to_numeric(rows["v"], errors="coerce"))
    .set_index("period")[["wind_mwh"]]
)
print(df)
print(f"{len(df)} months, {df['wind_mwh'].sum() / 1000:,.1f} GWh gross")
