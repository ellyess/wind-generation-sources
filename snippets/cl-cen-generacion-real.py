# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly delivered energy per Chilean wind plant for one day from CEN's SIP API (generacion-real).

Each record is one plant (idCentral) and one hour: a date (fecha), an hour number (hora, 1 to 24)
and a value in MWh. CEN states no time zone; records saved in July 2026 follow Chilean clock time
with daylight saving and stamp hora N at (N - 1):00, so hora N is read as the hour starting at
(N - 1):00 America/Santiago and converted to UTC. Values are after curtailment.

Traps handled:
- The technology filter must be "Eólica", with the accent; without it the list comes back empty.
- Results arrive under "data", not the "content" the schema advertises; both are accepted.
- Paging with page and limit returns HTTP 502, so pageSize is sent alone, above a day's rows.
- On clock-change days hora 25 (autumn) cannot be placed, and spring's missing hour is zero-filled;
  hours that do not exist or are ambiguous in local time are dropped and counted.
- The key goes in the URL (user_key), so request errors are reported without the URL.

Written from https://portal.api.coordinador.cl/swagger/spec/sip.json and the entry's notes on
2026-11-07; not yet run with a key. Without a key the endpoint answers 403 "Authentication
parameters missing".
"""
# wgs: needs CEN_API_KEY

import os

import pandas as pd
import requests

DAY = "2024-01-15"  # a Chilean calendar day with no clock change

try:
    resp = requests.get(
        "https://sipub.api.coordinador.cl/generacion-real/v3/findByDate", timeout=120,
        params={"startDate": DAY, "endDate": DAY, "tipoTecnologia": "Eólica", "pageSize": 5000,
                "user_key": os.environ["CEN_API_KEY"]})
except requests.RequestException as err:  # the message would carry the key in the URL
    raise SystemExit(f"request failed: {type(err).__name__}") from None
if resp.status_code != 200:
    raise SystemExit(f"HTTP {resp.status_code}: {resp.text[:300]}")
body = resp.json()
rows = pd.DataFrame(body.get("data", body.get("content")))
value = "gen_real_mw" if "gen_real_mw" in rows else "valor"  # saved records vs the schema

hora = pd.to_numeric(rows["hora"])
local = pd.to_datetime(rows["fecha"]) + pd.to_timedelta(hora - 1, unit="h")
rows["time_utc"] = (local.where(hora <= 24).dt.tz_localize(
    "America/Santiago", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC"))
print(f"dropped {rows['time_utc'].isna().sum()} plant-hours that cannot be placed in local time")

df = (
    rows.dropna(subset=["time_utc"])
    .assign(unit_id=lambda d: d["nombreCentralUnidad"],
            wind_mwh=lambda d: pd.to_numeric(d[value]))
    .set_index("time_utc").sort_index()[["unit_id", "idCentral", "wind_mwh"]]
)
print(df)
print(f"{len(df)} plant-hours, {df['unit_id'].nunique()} plants, "
      f"{df['wind_mwh'].sum() / 1000:.1f} GWh")
