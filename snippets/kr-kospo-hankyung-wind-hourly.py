# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly energy of the Hankyung wind farm on Jeju, both phases, from KOSPO via data.go.kr.

The file (2013-01-01 to 2026-03-31, 1.3 MB) has one row per day and phase (단계), with hourly
energy in kWh in columns 1 to 24. It is fetched through the portal's own download calls
(undocumented), after its download-limit check; if the portal asks for a CAPTCHA the script
stops. No time zone is stated; stamps are read as Korea Standard Time (UTC+9, no daylight
saving). Traps handled:
- the wide layout is melted to long form, and column h is read as the hour ending at h:00
  (24 is the last hour of the day, which the page states), so its start is h - 1;
- the file is CP949 (EUC-KR) encoded;
- phase 1 has two different rows for 30 January 2023, and which is right cannot be told, so
  both are dropped;
- a few cells hold "-" (19 August 2025, for example) or are empty; they are read as missing
  and dropped, not as zero;
- values are kWh per hour and are turned into MWh.
"""

import io

import pandas as pd
import requests

SITE = "https://www.data.go.kr"
PK, DETAIL = "15043410", "uddi:a2a4230d-e033-414d-8338-d37903d5e647"  # release of 2026-04-14

meta = requests.post(f"{SITE}/tcs/dss/selectFileDataDownload.do", timeout=60, data={
    "publicDataPk": PK, "publicDataDetailPk": DETAIL, "fileDetailSn": "1",
    "publicDataTyCode": "PR0051"}).json()
file = {"atchFileId": meta["atchFileId"], "fileDetailSn": meta["fileDetailSn"]}
limit = requests.post(f"{SITE}/cmm/cmm/check-limit.json", data=file, timeout=60).json()
if limit["needCaptcha"]:
    raise SystemExit("data.go.kr asks for a CAPTCHA: download the file by hand instead")
resp = requests.get(f"{SITE}/cmm/cmm/fileDownload.do", timeout=120,
                    params={**file, "dataNm": meta["dataSetFileDetailInfo"]["dataNm"]})
resp.raise_for_status()
wide = pd.read_csv(io.BytesIO(resp.content), encoding="cp949")

wide = wide.rename(columns={"년월일": "date", "단계": "unit_id"})
wide = wide[~wide.duplicated(["date", "unit_id"], keep=False)]  # drop both copies
hours = [str(h) for h in range(1, 25)]
long = wide.melt(id_vars=["date", "unit_id"], value_vars=hours, var_name="hour",
                 value_name="kwh")
long["kwh"] = pd.to_numeric(long["kwh"], errors="coerce")  # "-" -> missing
long = long.dropna(subset=["kwh"])
start = pd.to_datetime(long["date"]) + pd.to_timedelta(long["hour"].astype(int) - 1, unit="h")
df = (
    long.assign(time_utc=start.dt.tz_localize("Asia/Seoul").dt.tz_convert("UTC"),
                unit_id="phase " + long["unit_id"].astype(str),
                wind_mwh=long["kwh"] / 1000)  # kWh -> MWh
    .set_index("time_utc")
    .sort_index()[["unit_id", "wind_mwh"]]
)
print(df)
print(f"{len(df)} unit-hours, {df['wind_mwh'].sum() / 1000:.1f} GWh")
