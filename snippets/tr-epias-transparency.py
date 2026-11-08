# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Turkish national wind output for one day from EPİAŞ's settlement-based generation service.

POST /v1/generation/data/injection-quantity returns one item per hour with a "date" (ISO 8601,
+03:00), an "hour" and a value per source; "wind" is kept. EPİAŞ describes it as the electricity
given to the system hourly by the settlement units. It states no unit and does not say whether
the hour starts or ends the period; MWh per hour is assumed here and the stamp is kept as
given, so check a total against an annual figure before relying on it. Turkey has kept +03:00
all year since 2016.

Traps handled:
- The plant filter (powerplantId) is silently ignored and the national series comes back, so no
  plant is asked for and the result is labelled national.
- Access is by login: a ticket (TGT, valid two hours) is fetched from EPİAŞ's documented CAS
  endpoint with the account's email and password, then sent in a TGT header.
- "date" and "hour" should agree; the snippet stops if they do not, rather than guess.

Written from https://seffaflik.epias.com.tr/electricity-service/technical/en/index.html on
2026-11-07; not yet run with credentials. Without a TGT the service answers 401, error AUTH002.
Needs EPIAS_USERNAME and EPIAS_PASSWORD.
"""
# wgs: needs EPIAS_USERNAME

import os

import pandas as pd
import requests

START, END = "2024-01-15T00:00:00+03:00", "2024-01-15T23:00:00+03:00"  # one Turkish day

tgt = requests.post(
    "https://giris.epias.com.tr/cas/v1/tickets",
    data={"username": os.environ["EPIAS_USERNAME"], "password": os.environ["EPIAS_PASSWORD"]},
    headers={"Accept": "text/plain"},
    timeout=60,
)
tgt.raise_for_status()  # 201 Created, body "TGT-..."

resp = requests.post(
    "https://seffaflik.epias.com.tr/electricity-service/v1/generation/data/injection-quantity",
    json={"startDate": START, "endDate": END},
    headers={"TGT": tgt.text.strip(), "Accept": "application/json"},
    timeout=60,
)
resp.raise_for_status()
items = pd.DataFrame(resp.json()["items"])

local = pd.to_datetime(items["date"], format="ISO8601")  # carries +03:00
assert (local.dt.hour == items["hour"].astype(int)).all(), "date and hour disagree"
df = (
    pd.DataFrame({"time_utc": local.dt.tz_convert("UTC"), "wind_mwh": items["wind"]})
    .set_index("time_utc").sort_index()
)
print(df)
print(f"{len(df)} hours, {df['wind_mwh'].sum() / 1000:.1f} GWh (national; unit assumed MWh)")
