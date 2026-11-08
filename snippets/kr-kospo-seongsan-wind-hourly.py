# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly energy of the Seongsan wind farm on Jeju, both phases, from KOSPO via data.go.kr.

The file (2013-01-01 to 2026-03-31, 1.4 MB) has one row per day and phase (단계: 1 is turbines
1 to 6, 2 is turbines 7 to 10), with hourly energy in kWh in columns 1 to 24. It is fetched
through the portal's own download calls (undocumented), after its download-limit check; if the
portal asks for a CAPTCHA the script stops. No time zone is stated, so stamps are kept as a
naive `time` (Korea Standard Time, UTC+9, is likely but not stated). Traps handled:
- the wide layout is melted to long form, and column h is read as the hour ending at h:00
  (the page does not say), so its start is h - 1;
- a "-" (24 August 2024) and five empty cells are read as missing and dropped, not as zero;
- the file is CP949 (EUC-KR) encoded; kWh are turned into MWh.
Not fixed in code: from 2020 to 2022 the split between the phases shifts, so the farm total
(printed by year) is safer than either phase; two single hours are far too high.
"""

import io

import pandas as pd
import requests

SITE = "https://www.data.go.kr"
PK, DETAIL = "15043393", "uddi:74b8728d-96f7-46f4-a9d7-fd2005896558"  # release _20260331

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
hours = [str(h) for h in range(1, 25)]
long = wide.melt(id_vars=["date", "unit_id"], value_vars=hours, var_name="hour",
                 value_name="kwh")
long["kwh"] = pd.to_numeric(long["kwh"], errors="coerce")  # "-" -> missing
long = long.dropna(subset=["kwh"])
start = pd.to_datetime(long["date"]) + pd.to_timedelta(long["hour"].astype(int) - 1, unit="h")
df = (
    long.assign(time=start,  # zone not stated
                unit_id="phase " + long["unit_id"].astype(str),
                wind_mwh=long["kwh"] / 1000)  # kWh -> MWh
    .set_index("time")
    .sort_index()[["unit_id", "wind_mwh"]]
)
farm = df["wind_mwh"].groupby(df.index.year).sum() / 1000
print(df)
print(f"{len(df)} unit-hours, {df['wind_mwh'].sum() / 1000:.1f} GWh; farm GWh by year: "
      + ", ".join(f"{y} {v:.1f}" for y, v in farm.items()))
