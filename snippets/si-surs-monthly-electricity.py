# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Slovenia monthly wind production (GWh), gross and net, for one year from SiStat table 1817601S.

Statistical Office of Slovenia (SURS) electricity table, through its PxWeb API (one JSON POST).
Codes 10600 and 20600 are gross and net production from wind energy. Traps handled:
- recent months are provisional, which SURS marks only in the month's label text
  ("2026M09 (provisional data)"), so the labels are read from the table's metadata and kept
  as a provisional column;
- months before January 2015 are "-" (no data), read as missing rather than zero;
- August 2025 has net above gross (0.540 against 0.370 GWh), which cannot be right, so months
  where net exceeds gross are flagged in a net_above_gross column.
The national fleet is a few megawatts, so one turbine outage moves the figure.
"""

import pandas as pd
import requests

YEAR = 2025
URL = "https://pxweb.stat.si/SiStatData/api/v1/en/Data/1817601S.px"

meta = requests.get(URL, timeout=60).json()
month = next(v for v in meta["variables"] if v["code"] == "MESEC")
labels = dict(zip(month["values"], month["valueTexts"], strict=True))

months = [f"{YEAR}M{m:02d}" for m in range(1, 13)]
resp = requests.post(URL, json={
    "query": [{"code": "MERITVE", "selection": {"filter": "item", "values": ["10600", "20600"]}},
              {"code": "MESEC", "selection": {"filter": "item", "values": months}}],
    "response": {"format": "json"}}, timeout=60)
resp.raise_for_status()
rows = pd.DataFrame([r["key"] + r["values"] for r in resp.json()["data"]],
                    columns=["measure", "month", "value"])
rows["measure"] = rows["measure"].map({"10600": "gross_wind_gwh", "20600": "net_wind_gwh"})

df = (
    rows.assign(value=pd.to_numeric(rows["value"], errors="coerce"))  # "-" -> NaN
    .pivot(index="month", columns="measure", values="value")
    .rename_axis(columns=None)
)
df["provisional"] = df.index.map(lambda m: "provisional" in labels[m])
df["net_above_gross"] = df["net_wind_gwh"] > df["gross_wind_gwh"]  # August 2025
df.index = df.index.str.replace("M", "-").rename("period")  # 2025M09 -> 2025-09
print(df)
print(f"{len(df)} months, {df['gross_wind_gwh'].sum():.2f} GWh gross, "
      f"{df['net_wind_gwh'].sum():.2f} GWh net")
