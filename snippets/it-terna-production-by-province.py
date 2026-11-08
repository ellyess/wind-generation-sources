# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Italian wind production per province for one year, Terna statistical data (download centre).

The download centre's data service (undocumented: the JSON POST its own table makes) returns
annual production in GWh by region, province and renewable source. Traps handled:
- each province has a gross (Lorda) and a net (Netta) row; only gross is kept, so the total
  is not counted twice;
- the request needs orderByColumn, or the service answers HTTP 500;
- Sardinia's provinces differ between years (Sud Sardegna replaced four older provinces), so
  compare Sardinia by region across years.
"""

import pandas as pd
import requests

YEAR = "2024"
body = {"filterDataset": "ProductionRenewableSources", "filterSource": "Eolico",
        "filterYear": YEAR, "orderByColumn": "Anno", "orderByDir": "desc",
        "pageSize": "5000", "pageIndex": "0", "db": "dati"}
resp = requests.post("https://dati.terna.it/api/sitecore/dati/downloadcenter/recordsv2",
                     json=body, timeout=60)
resp.raise_for_status()
js = resp.json()
rows = pd.DataFrame(js["Data"], columns=list(js["Columns"]))
assert len(rows) == js["Count"] and set(rows["Fonte rinnovabile"]) == {"Eolico"}

gross = rows[rows["Tipo produzione"] == "Lorda"]
df = (
    gross.assign(period=gross["Anno"].astype(str))
    .rename(columns={"Regione": "region", "Provincia": "province",
                     "Produzione (GWh)": "wind_gwh"})
    .set_index("period")[["region", "province", "wind_gwh"]]
    .sort_values("wind_gwh", ascending=False)
)
print(df)
print(f"{len(df)} provinces, {df['wind_gwh'].sum():,.1f} GWh gross "
      f"({(df['wind_gwh'] > 0).sum()} with wind)")
