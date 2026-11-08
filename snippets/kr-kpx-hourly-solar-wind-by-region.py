# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly traded wind energy in Korea for 2025, mainland and Jeju, from KPX via data.go.kr.

The 2025 release (6.3 MB CSV) gives market trading volumes in MWh per trading date and trading
hour, sent-out, for solar by province and wind for the mainland (육지) and Jeju (제주도). It is
fetched through the portal's own download calls (undocumented), after its download-limit check;
if the portal asks for a CAPTCHA the script stops. No time zone is stated, so stamps are kept as a
naive `time` (Korea Standard Time, UTC+9, is likely but not stated). Traps handled:
- hours run 01 to 24, with 24 the last hour of the day, so hour h starts at h - 1;
- solar rows share the file and are dropped; wind is kept per region, long form;
- the file is CP949 (EUC-KR) encoded.
Not fixable in code: plants selling directly to KEPCO are excluded, so this is not national
wind output, and wind values include associated battery storage.
"""

import io

import pandas as pd
import requests

SITE = "https://www.data.go.kr"
PK, DETAIL = "15065269", "uddi:76850689-e74c-402e-bfec-9142976b96c8"  # release _20251231

meta = requests.post(f"{SITE}/tcs/dss/selectFileDataDownload.do", timeout=60, data={
    "publicDataPk": PK, "publicDataDetailPk": DETAIL, "fileDetailSn": "1",
    "publicDataTyCode": "PR0051"}).json()
file = {"atchFileId": meta["atchFileId"], "fileDetailSn": meta["fileDetailSn"]}
limit = requests.post(f"{SITE}/cmm/cmm/check-limit.json", data=file, timeout=60).json()
if limit["needCaptcha"]:
    raise SystemExit("data.go.kr asks for a CAPTCHA: download the file by hand instead")
resp = requests.get(f"{SITE}/cmm/cmm/fileDownload.do", timeout=300,
                    params={**file, "dataNm": meta["dataSetFileDetailInfo"]["dataNm"]})
resp.raise_for_status()
rows = pd.read_csv(io.BytesIO(resp.content), encoding="cp949", dtype={"거래시간": str})

wind = rows[rows["연료원"] == "풍력"]  # wind; 태양광 is solar
start = pd.to_datetime(wind["거래일"]) + pd.to_timedelta(wind["거래시간"].astype(int) - 1, "h")
df = (
    wind.assign(time=start,  # zone not stated
                region=wind["지역"].map({"육지": "mainland", "제주도": "jeju"}))
    .rename(columns={"전력거래량(MWh)": "wind_mwh"})
    .set_index("time")
    .sort_index()[["region", "wind_mwh"]]
)
print(df)
print(f"{len(df)} region-hours, {df['wind_mwh'].sum() / 1000:.0f} GWh "
      f"(Jeju {df.loc[df['region'] == 'jeju', 'wind_mwh'].sum() / 1000:.0f} GWh)")
