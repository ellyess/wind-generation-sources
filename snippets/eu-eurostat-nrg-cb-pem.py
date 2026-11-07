# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Monthly net wind electricity generation per country from Eurostat (nrg_cb_pem), for 2024.

Wind is product RA300; the request filters on unit=GWH (the other unit, PC, is a share of the
total). Values are calendar-month totals in GWh, labelled like 2024-01. Traps handled: the
status flags ("e" estimated, "p" provisional), which many German months carry, are kept in a
column instead of being lost; Greece (EL) and the United Kingdom (UK) are mapped to the ISO
codes GR and GB; EU aggregates are dropped. Not handled here: wind is zero-filled before 2011,
so do not read early zeros as calm years, and summed months can exceed the annual table
(eu-eurostat-nrg-bal-peh).
"""

import pandas as pd
import requests

resp = requests.get(
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_cb_pem",
    params={"siec": "RA300", "unit": "GWH", "sinceTimePeriod": "2024-01",
            "untilTimePeriod": "2024-12", "format": "JSON", "lang": "en"},
    timeout=60,
)
resp.raise_for_status()
js = resp.json()

# JSON-stat: values and flags are keyed by their flat position in the product of dimensions
cats = [js["dimension"][d]["category"]["index"] for d in js["id"]]
cells = pd.MultiIndex.from_product([sorted(c, key=c.get) for c in cats], names=js["id"])
values = pd.Series(js["value"]).rename(index=int)
flags = pd.Series(js.get("status", {}), dtype="object").rename(index=int)
rows = cells[values.index].to_frame(index=False).assign(
    wind_gwh=values.to_numpy(), status=flags.reindex(values.index).fillna("").to_numpy())

df = (
    rows[~rows["geo"].str.startswith(("EU", "EA"))]
    .assign(country=lambda d: d["geo"].replace({"EL": "GR", "UK": "GB"}))
    .rename(columns={"time": "period"})
    .set_index("period")[["country", "wind_gwh", "status"]]
    .sort_values(["country", "period"])
)
print(df)
flagged = (df["status"] != "").sum()
print(f"{len(df)} country-months ({flagged} flagged), {df['wind_gwh'].sum() / 1000:.0f} TWh in all")
