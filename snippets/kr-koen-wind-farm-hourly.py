# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly energy of Korea South-East Power's (KOEN) wind farms, one month, from KOEN's own site.

KOEN's page "시간대별 풍력 발전실적" serves a CSV for any period of up to a month: one row per day
and farm (발전구분, with 호기 the phase), the 24 hours as columns "1시 발전량(MWh)" to "24시".
Data start in January 2022. No time zone is stated, so stamps are kept as a naive `time`, not
UTC (Korea Standard Time, UTC+9, is likely but not stated). Traps handled:
- the header says MWh per hour and KW for the daily total, but the values are kWh (Yeongheung
  phase 2, 24 MW, peaks near 25,000 in an hour), so kWh are turned into MWh;
- column h is read as the hour ending at h:00 (the page does not say), so its start is h - 1;
- every data row ends with a comma the header lacks, so pandas must not use column 1 as index.
Not fixed in code: a few hours exceed the stated capacity, and the latest month can lack farms.
"""

import io

import pandas as pd
import requests

URL = "https://www.koenergy.kr/kosep/gv/nf/dt/nfdt23/csvDown.do"
resp = requests.post(URL, timeout=60, data={
    "menuCd": "FN0912020218", "pageIndex": "1", "strOrgNo": "", "strHokiS": "", "strHokiE": "",
    "strDateS": "20260101", "strDateE": "20260131"})
resp.raise_for_status()
wide = pd.read_csv(io.BytesIO(resp.content), encoding="utf-8-sig", skipinitialspace=True,
                   index_col=False)
wide.columns = [c.strip() for c in wide.columns]
wide["unit_id"] = wide["발전구분"].str.strip() + " " + wide["호기"].astype(str)
hours = [c for c in wide.columns if "시 발전량" in c]
long = wide.melt(id_vars=["일자", "unit_id"], value_vars=hours, var_name="hour",
                 value_name="kwh")
hour = long["hour"].str.extract(r"^(\d+)")[0].astype(int)
start = pd.to_datetime(long["일자"].str.strip()) + pd.to_timedelta(hour - 1, unit="h")
df = (
    long.assign(time=start,  # zone not stated
                wind_mwh=pd.to_numeric(long["kwh"], errors="coerce") / 1000)  # kWh -> MWh
    .dropna(subset=["wind_mwh"])
    .set_index("time")
    .sort_index()[["unit_id", "wind_mwh"]]
)
by_farm = df.groupby("unit_id")["wind_mwh"].agg(["sum", "max"]).round(1)
print(df)
print(by_farm)
print(f"{len(df)} unit-hours, {df['wind_mwh'].sum():.0f} MWh in January 2026")
