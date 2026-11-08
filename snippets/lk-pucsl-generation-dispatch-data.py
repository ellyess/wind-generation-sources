# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Sri Lanka's telemetered wind dispatch for one day at 15 minutes, from PUCSL's data portal.

The calls are the ones the dashboard at gendata.pucsl.gov.lk makes itself (undocumented, no
key). Times go in and come out in UTC; Sri Lanka is UTC+5:30 all year. A query longer than a
day or two at 15 minutes times out, so this asks for one day. Traps handled:
- the 15-minute series is all telemetered wind (state utility and private producers together)
  but is filed under the plant named "Wind (IPP)"; in the daily statistics the same id is the
  private producers only, and "Wind (CEB)" is the state utility's Mannar farm;
- stamps run 00:15 to 24:00 local, which fits period ends, but PUCSL does not say which end a
  stamp marks, so stamps are kept as published, not moved to a period start (nor whether a
  value is a mean or a reading);
- 15-minute values are MW (dispatchValueInMW); daily totals are MWh, and are larger because
  the 15-minute series covers telemetered plants only.
"""

import pandas as pd
import requests

API = "https://gendata.pucsl.gov.lk/api"
DAY = pd.Timestamp("2024-04-01", tz="Asia/Colombo")  # one local day
iso = "%Y-%m-%dT%H:%M:%S.000Z"
span = {"from": (DAY + pd.Timedelta("15min")).tz_convert("UTC").strftime(iso),  # 00:15 label
        "to": (DAY + pd.Timedelta("1D")).tz_convert("UTC").strftime(iso)}  # 24:00 label

plants = requests.get(f"{API}/metadata/power-plants", timeout=60).json()["data"]
ids = {p["name"]: p["id"] for p in plants}
ipp, ceb = ids["Wind (IPP)"], ids["Wind (CEB)"]

rows = requests.get(f"{API}/actual-system-dispatch", timeout=120,
                    params={"dateAggregation": "15min", **span}).json()["data"]
wind = pd.DataFrame([r for r in rows if r["powerPlantId"] == ipp])
stamp = pd.to_datetime(wind["reportTimestamp"], utc=True)  # stamp end not stated
df = (
    wind.assign(time_utc=stamp, wind_mw=wind["dispatchValueInMW"])
    .set_index("time_utc")
    .sort_index()[["wind_mw"]]
)

start = DAY.tz_convert("UTC").strftime(iso)  # a day is stamped at local midnight
daily = requests.get(f"{API}/daily-generation-statistics", timeout=120, params={
    "dateAggregation": "day", "from": start, "to": start}).json()["data"]
mwh = {r["powerPlantId"]: r["dailyTotalEnergyInMwh"] for r in daily}
print(df)
print(f"{len(df)} quarter-hours, {df['wind_mw'].sum() / 4:.0f} MWh telemetered; daily report: "
      f"private {mwh[ipp]} MWh + state utility {mwh[ceb]} MWh = {mwh[ipp] + mwh[ceb]} MWh")
