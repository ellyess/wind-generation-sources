# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Latvian wind generation by municipality and State city for one year, CSB table ENA050.

A PxWeb query for wind power stations over every territorial unit returns annual electricity
generated in GWh, as json-stat2. Traps handled:
- for 2025, areas with no wind show "-" (a null value) instead of 0. The table's own
  json-stat note says "- = Magnitude zero", so they are set to 0 here and kept visible in a
  `flag` column;
- statistical region boundaries changed on 1 January 2024, and the country and region rows sit
  among the municipalities, so only municipalities and State cities are kept, and their sum is
  checked against the Latvia row.
"""

import pandas as pd
import requests

YEAR = "2025"
URL = "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/NOZ/EN/ENA/ENA050"
query = {
    "query": [
        {"code": "PLANTS_REN", "selection": {"filter": "item", "values": ["WT"]}},  # wind
        {"code": "AREA", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "TIME", "selection": {"filter": "item", "values": [YEAR]}},
    ],
    "response": {"format": "json-stat2"},
}
resp = requests.post(URL, json=query, timeout=60)
resp.raise_for_status()
js = resp.json()
assert "- = Magnitude zero" in js["note"]

area = js["dimension"]["AREA"]["category"]
codes = sorted(area["index"], key=area["index"].get)  # one value per area, in index order
rows = pd.DataFrame({
    "area_id": codes,
    "area": [area["label"][c] for c in codes],
    "wind_gwh": js["value"],
    "flag": [js.get("status", {}).get(str(i), "") for i in range(len(codes))],
})
rows["wind_gwh"] = rows["wind_gwh"].where(rows["flag"] != "-", 0.0).astype(float)
latvia = rows.loc[rows["area_id"].eq("LV"), "wind_gwh"].item()

df = rows[rows["area_id"].str.len() == 9].assign(period=YEAR).set_index("period")
print(df)
print(f"{len(df)} municipalities and cities, {df['wind_gwh'].sum():.3f} GWh "
      f"(Latvia row: {latvia:.3f} GWh)")
