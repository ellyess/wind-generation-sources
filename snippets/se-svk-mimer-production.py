# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Sweden hourly settled wind energy (kWh) per bidding zone for one day from Svenska kraftnät Mimer.

Mimer's text download gives one row per hour, "Avräknad (kWh)" (settled energy in the hour),
with a publication time. Traps handled:
- labels behave as Swedish standard time (UTC+1) all year, marking the hour start (observed by
  matching eSett's UTC data; Svenska kraftnät does not say so), so one hour is subtracted;
- values use a decimal comma and ";" separators, and the file ends with a "Summa" row, dropped;
- gaps are filled with exact zeros, which look like calm hours: on the sample day, the spring
  clock change of 31 March 2024, every zone has 0 at 03:00. Isolated zeros and trailing runs
  of zeros are set to missing.
Discontinued: values end in October 2025; later data are on eSett Open Data.
"""

import io

import pandas as pd
import requests

DAY = pd.Timestamp("2024-03-31")

frames = []
for zone in ["SN1", "SN2", "SN3", "SN4"]:  # SE1 to SE4
    resp = requests.get(
        "https://mimer.svk.se/ProductionConsumption/DownloadText",
        params={"PeriodFrom": DAY.strftime("%m/%d/%Y 00:00:00"),
                "PeriodTo": DAY.strftime("%m/%d/%Y 00:00:00"),  # the end day is included
                "ConstraintAreaId": zone, "ProductionSortId": "VI"},  # VI = wind
        timeout=60,
    )
    resp.raise_for_status()
    rows = pd.read_csv(io.StringIO(resp.content.decode("utf-8-sig")), sep=";", decimal=",",
                       usecols=[0, 1, 2], names=["period", "wind_kwh", "published"], skiprows=1)
    rows = rows[rows["period"] != "Summa"]
    zero = rows["wind_kwh"].eq(0)
    isolated = zero & ~zero.shift(1, fill_value=False) & ~zero.shift(-1, fill_value=False)
    trailing = zero[::-1].cummin()[::-1]
    frames.append(rows.assign(zone=f"SE{zone[-1]}",
                              wind_kwh=rows["wind_kwh"].mask(isolated | trailing)))
rows = pd.concat(frames)

utc = pd.to_datetime(rows["period"]) - pd.Timedelta(hours=1)  # UTC+1 -> UTC
df = (
    rows.assign(time_utc=utc.dt.tz_localize("UTC"))
    .set_index("time_utc")
    .sort_index()[["zone", "wind_kwh", "published"]]
)
print(df)
print(f"{len(df)} zone-hours, {df['wind_kwh'].isna().sum()} zeros set to missing, "
      f"{df['wind_kwh'].sum() / 1e6:,.1f} GWh")
