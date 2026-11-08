# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly energy sent out by the Sangmyeong wind farm on Jeju, from KOMIPO via data.go.kr.

The file (2023-01-01 to 2026-03-30, 215 kB) has one row per day, with hourly energy in columns
1시 to 24시. It is fetched through the portal's own download calls (undocumented), after its
download-limit check; if the portal asks for a CAPTCHA the script stops. No time zone is
stated, so stamps are kept as a naive `time` (Korea Standard Time, UTC+9, is likely but not
stated). Traps handled:
- the page says kWh in its description and MWh in its column list; the data only fit kWh;
- every value before 2025-02-01 is 1,000 times too large (the decimal point was dropped), so
  those rows are divided by 1,000;
- column h is read as the hour ending at h:00 (the page does not say), so its start is h - 1;
- blank days (31 January 2026, for example) and the empty last row are dropped, not zeroed;
- the file is CP949 (EUC-KR) encoded; kWh are turned into MWh.
"""

import io

import pandas as pd
import requests

SITE = "https://www.data.go.kr"
PK, DETAIL = "15119454", "uddi:3a718cc1-7509-454a-95fd-a73e8da11e9a"  # release _20260330

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
wide = pd.read_csv(io.BytesIO(resp.content), encoding="cp949").dropna(subset=["기준일"])

hours = [f"{h}시" for h in range(1, 25)]
long = wide.melt(id_vars=["기준일"], value_vars=hours, var_name="hour", value_name="kwh")
long = long.dropna(subset=["kwh"])
date = pd.to_datetime(long["기준일"])
long["kwh"] = long["kwh"].where(date >= "2025-02-01", long["kwh"] / 1000)  # dropped decimals
start = date + pd.to_timedelta(long["hour"].str[:-1].astype(int) - 1, unit="h")
df = (
    long.assign(time=start,  # zone not stated
                wind_mwh=long["kwh"] / 1000)  # kWh -> MWh
    .set_index("time")
    .sort_index()[["wind_mwh"]]
)
yearly = df["wind_mwh"].groupby(df.index.year).sum() / 1000
print(df)
print(f"{len(df)} hours, max {df['wind_mwh'].max():.2f} MWh in an hour (21 MW farm); GWh by year: "
      + ", ".join(f"{y} {v:.1f}" for y, v in yearly.items()))
