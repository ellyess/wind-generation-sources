# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly SCADA power of the eight Hwasun turbines for one month, from KOWEPO via data.go.kr.

The only file (2015-12 to 2025-12) is 79 MB and slow to serve, so this streams it and stops
after the first month, December 2015; its rows run in time order with all eight turbines each
hour. It is fetched through the portal's own download calls (undocumented), after its
download-limit check; if the portal asks for a CAPTCHA the script stops. The page gives the
power as grid active power in kW but not whether an hourly value is a mean or a sample, nor
the stamp end or time zone, so stamps (hours 00 to 23) are kept as published, a naive
`time` (Korea Standard Time, UTC+9, is likely but not stated). Traps handled:
- the file is CP949 (EUC-KR) encoded;
- power is kW, not energy, and dips slightly negative at idle; it is kept as power, and the
  printed energy is the net sum (negatives included);
- turbine 1's longitude is about a degree west of the rest, so outlying coordinates are flagged.
"""

import io

import pandas as pd
import requests

SITE = "https://www.data.go.kr"
PK, DETAIL = "15159036", "uddi:24d2f321-6e4d-42d2-a58b-b62ad83561aa"
STOP = "2016-01-01"  # first stamp not read

meta = requests.post(f"{SITE}/tcs/dss/selectFileDataDownload.do", timeout=60, data={
    "publicDataPk": PK, "publicDataDetailPk": DETAIL, "fileDetailSn": "1",
    "publicDataTyCode": "PR0051"}).json()
file = {"atchFileId": meta["atchFileId"], "fileDetailSn": meta["fileDetailSn"]}
limit = requests.post(f"{SITE}/cmm/cmm/check-limit.json", data=file, timeout=60).json()
if limit["needCaptcha"]:
    raise SystemExit("data.go.kr asks for a CAPTCHA: download the file by hand instead")
lines = []
with requests.get(f"{SITE}/cmm/cmm/fileDownload.do", stream=True, timeout=120,
                  params={**file, "dataNm": meta["dataSetFileDetailInfo"]["dataNm"]}) as resp:
    resp.raise_for_status()
    for raw in resp.iter_lines():
        line = raw.decode("cp949")
        if not line:
            continue  # iter_lines can split a CRLF into an empty line
        if lines and line[:10] >= STOP:
            break  # the rest of the file is later months
        lines.append(line)
rows = pd.read_csv(io.StringIO("\n".join(lines)))

lon = rows.groupby("발전호기")["경도(십진수)"].first()
odd = lon[(lon - lon.median()).abs() > 0.5]
start = pd.to_datetime(rows["일자(1시간단위)"], format="%Y-%m-%d %H")
df = (
    rows.assign(time=start)  # zone and stamp end not stated
    .rename(columns={"발전호기": "unit_id", "계통 유효 전력(킬로와트)": "power_kw",
                     "나셀 풍속(초당 미터)": "wind_speed_ms"})
    .set_index("time")
    .sort_index()[["unit_id", "power_kw", "wind_speed_ms"]]
)
print(df)
print(f"Check coordinates of turbine(s) {list(odd.index)}: longitude {odd.tolist()}")
print(f"{len(df)} turbine-hours, {df['unit_id'].nunique()} turbines, "
      f"{df['power_kw'].sum() / 1e6:.2f} GWh net")  # kW x 1 h
