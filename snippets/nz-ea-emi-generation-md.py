# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""New Zealand half-hourly wind generation per farm for one month from the EMI Generation_MD files.

One CSV per month, one row per connection point and trading day, with kWh in trading periods
TP1 to TP50. Traps handled:
- trading periods follow New Zealand local time: TP1 starts at local midnight, and a day has
  46, 48 or 50 periods across daylight saving changes. Each period is placed at local midnight
  in UTC plus 30 minutes per period, so April 2026 (clocks back on 5 April) gets 50 there;
- unused TP49 and TP50 cells on ordinary days are dropped, not read as zero;
- farms metered at several connection points (West Wind, twf_12) are summed on Gen_Code,
  which is stable, rather than keyed on site codes, which are not;
- this file labels wind "Wind" for most farms but "WIN" for kaiwera_downs_(stage_2), so both
  are kept.
Not handled: Mahinerangi sits inside the Waipori hydro scheme, and small distribution-connected
farms are not in the dataset.
"""

import io

import pandas as pd
import requests

MONTH = "202604"
URL = ("https://www.emi.ea.govt.nz/Wholesale/Datasets/Generation/Generation_MD/"
       f"{MONTH}_Generation_MD.csv")

resp = requests.get(URL, timeout=60)  # redirects to the public blob store
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.text))
rows = rows[rows["Fuel_Code"].isin(["Wind", "WIN"])]

long = rows.melt(id_vars=["Gen_Code", "Trading_Date"], value_vars=[f"TP{i}" for i in range(1, 51)],
                 var_name="tp", value_name="wind_kwh").dropna(subset=["wind_kwh"])
midnight = pd.to_datetime(long["Trading_Date"]).dt.tz_localize("Pacific/Auckland")
midnight = midnight.dt.tz_convert("UTC")  # local midnight, in UTC
long["time_utc"] = midnight + pd.to_timedelta((long["tp"].str[2:].astype(int) - 1) * 30, unit="min")

df = (
    long.groupby(["time_utc", "Gen_Code"])["wind_kwh"].sum()  # add up connection points
    .reset_index(level="Gen_Code")
    .rename(columns={"Gen_Code": "unit_id"})
)
print(df)
per_day = long.groupby("Trading_Date")["tp"].nunique()
print(f"periods on 2026-04-05: {per_day.get('2026-04-05')}")
print(f"{len(df)} farm-half-hours, {df['unit_id'].nunique()} farms, "
      f"{df['wind_kwh'].sum() / 1e6:.1f} GWh")  # kWh / 1e6
