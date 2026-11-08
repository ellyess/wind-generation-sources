# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32", "truststore>=0.10"]
# ///
"""Swedish wind production and capacity per county for one year, Energimyndigheten EN0105_3.

Annual production in GWh and installed capacity in MW for each of the 21 counties (län), from
the agency's PxWeb API. Traps handled:
- the API's codes are positions, not names (År "21" is 2024), so labels are read from the
  table's metadata;
- ".." means data not available: some counties' production is withheld, so it is kept as
  missing and the county sum is compared with the national table EN0105_1;
- the server does not send its intermediate certificate, so truststore (the operating
  system's verifier) is used; verification stays on.
"""

import pandas as pd
import requests
import truststore

truststore.inject_into_ssl()

YEAR = "2024"
BASE = ("https://pxexternal.energimyndigheten.se/api/v1/en/Energimyndighetens_statistikdatabas/"
        "Officiell_energistatistik/Vindkraftsstatistik")


def table(name: str, year_code: str) -> pd.DataFrame:
    body = {"query": [{"code": "År", "selection": {"filter": "item", "values": [year_code]}}],
            "response": {"format": "json"}}
    resp = requests.post(f"{BASE}/{name}", json=body, timeout=60)
    resp.raise_for_status()
    keys = [c["code"] for c in resp.json()["columns"][:-1]]
    rows = [r["key"] + r["values"] for r in resp.json()["data"]]
    return pd.DataFrame(rows, columns=keys + ["value"])


def labels(name: str) -> dict:
    meta = requests.get(f"{BASE}/{name}", timeout=60).json()["variables"]
    return {v["code"]: dict(zip(v["values"], v["valueTexts"], strict=True)) for v in meta}


def year_code(lab: dict) -> str:
    return {text: code for code, text in lab["År"].items()}[YEAR]


lab = labels("EN0105_3.px")
rows = table("EN0105_3.px", year_code(lab))
rows["value"] = pd.to_numeric(rows["value"], errors="coerce")  # ".." -> missing
wide = rows.pivot(index="Län", columns="Kategori", values="value")
df = (
    pd.DataFrame({"county": wide.index.map(lab["Län"]), "wind_gwh": wide["2"],
                  "capacity_mw": wide["1"]})
    .assign(period=YEAR).set_index("period").sort_values("wind_gwh", ascending=False)
)
print(df)

whole = table("EN0105_1.px", year_code(labels("EN0105_1.px")))
national = float(whole.loc[whole["Kategori"] == "2", "value"].iloc[0])
print(f"{len(df)} counties ({df['wind_gwh'].isna().sum()} withheld), "
      f"{df['wind_gwh'].sum():,.1f} GWh summed; national {national:,.1f} GWh")
