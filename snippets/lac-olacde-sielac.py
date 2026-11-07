# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual wind production for one country from the energy balance in OLACDE's sieLAC API.

The energy balance for a year and country lists activities (such as "Production"), energy
sources with their unit, and one value per activity and source. The snippet finds the source
whose English name contains "wind" and the "Production" activity, and keeps the value in the
source's own unit (unitId left at its default, "original units"), read from the response. Which
countries report wind, and in what unit, is not documented; the snippet stops if no wind row.

Traps handled:
- Access is by credentials that OLACDE emails on request; the snippet exchanges them for a
  bearer token at the documented /token endpoint (valid 24 hours) and sends it on each call.
- Years are ids such as 202400 for 2024, and countries are ids, so both are looked up by name.

Written from https://sielacapi.olacde.org/ and https://sielacapi.olacde.org/Help on 2026-11-07;
not yet run with credentials. With empty credentials /token answers 400 "invalid_grant". The
terms forbid redistributing the data without OLACDE's authorisation. Needs OLACDE_USERNAME and
OLACDE_PASSWORD.
"""
# wgs: needs OLACDE_USERNAME

import os

import pandas as pd
import requests

API, COUNTRY, YEAR = "https://sielacapi.olacde.org", "Uruguay", "2023"

token = requests.post(f"{API}/token", timeout=60, data={
    "grant_type": "password", "username": os.environ["OLACDE_USERNAME"],
    "password": os.environ["OLACDE_PASSWORD"]})
token.raise_for_status()
auth = token.json()
s = requests.Session()
s.headers.update({"Authorization": f"{auth['token_type']} {auth['access_token']}",
                  "Accept-Language": "en"})


def get(path):
    resp = s.get(f"{API}/api/{path}", timeout=60)
    resp.raise_for_status()
    return resp.json()


time_id = next(t["Id"] for t in get("energyBalance/times") if t["Name"] == YEAR)
unit_id = next(u["Id"] for u in get("energyBalance/informationUnits") if u["Name"] == COUNTRY)
bal = get(f"energyBalance/{time_id}/{unit_id}")

sources = pd.DataFrame(bal["EnergySources"]).set_index("Id")
wind = sources[sources["Name"].str.contains("wind", case=False)]
assert len(wind) == 1, f"expected one wind source, found {list(wind['Name'])}"
production = next(a["Id"] for a in bal["Activities"] if a["Name"] == "Production")
data = pd.DataFrame(bal["Data"])
row = data[(data["ActivityId"] == production) & (data["EnergySourceId"] == wind.index[0])]

unit = wind["Unit"].iloc[0]
df = pd.DataFrame({"country": COUNTRY, "wind_production": row["Value"].to_numpy(), "unit": unit},
                  index=pd.Index([YEAR], name="period"))
print(df)
print(f"{len(df)} year, {COUNTRY} wind production {df['wind_production'].sum():,.1f} {unit}")
