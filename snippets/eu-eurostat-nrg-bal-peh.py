# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual gross wind electricity production per country from Eurostat (nrg_bal_peh).

Wind is product RA300 and gross electricity production is balance GEP. The table is also
published in KTOE and TJ, so the request filters on unit=GWH. Values are year totals in GWh,
labelled by year. Traps handled: Eurostat codes Greece as EL and the United Kingdom as UK, so
both are mapped to the ISO codes GR and GB; EU aggregates are dropped so the total is not
double counted. Gross production normally runs 5-15% above transmission operators' figures.
"""

import pandas as pd
import requests

resp = requests.get(
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_bal_peh",
    params={"siec": "RA300", "nrg_bal": "GEP", "unit": "GWH", "time": ["2023", "2024"],
            "format": "JSON", "lang": "en"},
    timeout=60,
)
resp.raise_for_status()
js = resp.json()

# JSON-stat: values are keyed by their flat position in the product of all dimensions
cats = [js["dimension"][d]["category"]["index"] for d in js["id"]]
cells = pd.MultiIndex.from_product([sorted(c, key=c.get) for c in cats], names=js["id"])
values = pd.Series(js["value"]).rename(index=int)
rows = cells[values.index].to_frame(index=False).assign(wind_gwh=values.to_numpy())

df = (
    rows[~rows["geo"].str.startswith(("EU", "EA"))]
    .assign(country=lambda d: d["geo"].replace({"EL": "GR", "UK": "GB"}))
    .rename(columns={"time": "period"})
    .set_index("period")[["country", "wind_gwh"]]
    .sort_values(["period", "country"])
)
print(df)
print(f"{len(df)} country-years, {df['wind_gwh'].sum() / 1000:.0f} TWh in all")
