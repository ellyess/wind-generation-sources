# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Netherlands onshore wind production and capacity per province for one year (CBS table 70960ned).

Annual production in million kWh (GWh) and year-end capacity in MW, from the CBS OData API.
Traps handled:
- two production columns exist; this keeps the actual one (NietGenormaliseerdeProductie_11),
  not the production normalised to an average wind year (GenormaliseerdeProductie_10);
- the national row (NL01) is dropped so the provinces can be summed without double counting.
Offshore wind is not in this table. Production is empty before 2002.
"""

import pandas as pd
import requests

YEAR = 2023  # definitive; later years are provisional

base = "https://opendata.cbs.nl/ODataApi/odata/70960ned"
resp = requests.get(
    f"{base}/TypedDataSet",
    params={"$filter": f"Perioden eq '{YEAR}JJ00'",
            "$select": "RegioS,NietGenormaliseerdeProductie_11,OpgesteldVermogenEindeJaar_9"},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["value"])
names = pd.DataFrame(requests.get(f"{base}/RegioS", timeout=60).json()["value"])
names = names.set_index(names["Key"].str.strip())["Title"]

rows["region_id"] = rows["RegioS"].str.strip()
rows = rows[rows["region_id"].str.startswith("PV")]  # provinces only, not NL01
df = (
    rows.assign(period=str(YEAR), province=rows["region_id"].map(names))
    .rename(columns={"NietGenormaliseerdeProductie_11": "wind_gwh",
                     "OpgesteldVermogenEindeJaar_9": "capacity_mw"})
    .set_index("period")[["region_id", "province", "wind_gwh", "capacity_mw"]]
)
print(df)
print(f"{len(df)} provinces, {df['wind_gwh'].sum():,.0f} GWh actual, "
      f"{df['capacity_mw'].sum():,.0f} MW at year end")
