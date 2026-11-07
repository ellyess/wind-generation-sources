# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual wind generation on Bonaire from CBS table 81154eng (Caribbean Netherlands).

The OData table gives electricity production per island and year in million kWh (GWh), split
into total, fossil and renewable. Traps handled:
- "Renewable" is defined as wind, but on Sint Eustatius and Saba it is mostly solar, so only
  the Bonaire row (GM9001) is read as a wind series;
- recent years are provisional; the period's status is kept in a "provisional" column.
Values are in million kWh to one decimal; million kWh equals GWh.
"""

import pandas as pd
import requests

BASE = "https://opendata.cbs.nl/ODataApi/odata/81154eng"


def get(path, **params):
    resp = requests.get(f"{BASE}/{path}", params=params, timeout=60)
    resp.raise_for_status()
    return pd.DataFrame(resp.json()["value"])


rows = get("TypedDataSet", **{"$filter": "CaribbeanNetherlands eq 'GM9001'",
                              "$select": "Periods,Total_6,Renewable_8"})
status = get("Periods").set_index("Key")["Status"]

df = (
    rows.dropna(subset=["Renewable_8"])
    .assign(period=lambda d: d["Periods"].str[:4],
            provisional=lambda d: d["Periods"].map(status).eq("Voorlopig"))
    .rename(columns={"Renewable_8": "wind_gwh", "Total_6": "total_gwh"})
    .set_index("period")[["wind_gwh", "total_gwh", "provisional"]]
)
print(df)
print(f"{len(df)} years, {df['wind_gwh'].sum():.1f} GWh of wind on Bonaire")
