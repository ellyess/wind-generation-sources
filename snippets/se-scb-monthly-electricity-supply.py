# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Swedish monthly wind production by bidding zone for one year, SCB table ElEO (PxWeb API).

Net production in GWh per month for SE1 to SE4 (category Vinkraft), labelled like 2024M01 and
turned into 2024-01 here; the data come from the Swedish Energy Agency. Traps handled:
- this zone table starts in 2021; the national table EltillfM goes back to 1997 and is used
  here as a check on the zone total;
- ".." marks a missing value and is read as missing, not zero.
"""

import pandas as pd
import requests

YEAR = 2024
BASE = "https://api.scb.se/OV0104/v1/doris/en/ssd/EN/EN0108/EN0108A"
months = [f"{YEAR}M{m:02d}" for m in range(1, 13)]
TIMEOUT = (10, 60)  # short connect timeout: falls back to IPv4 fast where IPv6 is unreachable


def query(table: str, code: str, value: str) -> dict:
    body = {"query": [{"code": code, "selection": {"filter": "item", "values": [value]}},
                      {"code": "Tid", "selection": {"filter": "item", "values": months}}],
            "response": {"format": "json"}}
    resp = requests.post(f"{BASE}/{table}", json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


zones = query("ElEO", "ProdAnv", "Vinkraft")
assert "in GWh" in zones["columns"][-1]["text"]
rows = pd.DataFrame([(r["key"][1], r["key"][2], r["values"][0]) for r in zones["data"]],
                    columns=["zone", "label", "wind_gwh"])
df = (
    rows.assign(period=rows["label"].str.replace("M", "-"),
                wind_gwh=pd.to_numeric(rows["wind_gwh"], errors="coerce"))
    .set_index("period")[["zone", "wind_gwh"]]
)
print(df)

national = query("EltillfM", "Prodslag", "Vind")
total = sum(float(r["values"][0]) for r in national["data"])
print(f"{len(df)} zone-months, {df['wind_gwh'].sum():,.0f} GWh across zones; "
      f"national table {total:,.0f} GWh")
