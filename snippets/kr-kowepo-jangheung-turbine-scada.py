# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""One month of 10-minute SCADA power for one Jangheung turbine, from KOWEPO via data.go.kr.

The only file (2022 to 2025, six 3 MW turbines) is 129 MB, with all of turbine 1 first, then
turbine 2 and so on. This streams it and stops after turbine 1's first month, January 2022,
so it is a one-turbine sample by design: do not read a partial download as the whole farm. It
is fetched through the portal's own download calls (undocumented), after its download-limit
check; if the portal asks for a CAPTCHA the script stops. Power is grid active power in kW
(10-minute values peak near 3,030 kW, so it is not energy per step). Whether values are means
or samples, the stamp end and the time zone are not stated, so stamps are kept as published,
a naive `time` (Korea Standard Time, UTC+9, is likely but not stated). Traps handled:
- the file is CP949 (EUC-KR) encoded;
- the step changes from 10 minutes to hourly in 2025; this sample is 10-minute only, and the
  step is printed so a longer read shows the change;
- power dips slightly negative at idle; the printed energy is the net sum.
"""

import io

import pandas as pd
import requests

SITE = "https://www.data.go.kr"
PK, DETAIL = "15159034", "uddi:634aa783-611b-44f7-9dd9-f70cec670eec"
STOP = "2022-02-01"  # first stamp not read

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
        if lines and (line[:10] >= STOP or line.split(",")[2] != "1"):
            break  # later months of turbine 1, then turbines 2 to 6
        lines.append(line)
rows = pd.read_csv(io.StringIO("\n".join(lines)))

start = pd.to_datetime(rows["일자"], format="%Y-%m-%d %H:%M")
df = (
    rows.assign(time=start)  # zone and stamp end not stated
    .rename(columns={"발전호기": "unit_id", "계통 유효 전력(킬로와트)": "power_kw",
                     "나셀 풍속(초당 미터)": "wind_speed_ms"})
    .set_index("time")
    .sort_index()[["unit_id", "power_kw", "wind_speed_ms"]]
)
step = df.index.to_series().diff().mode()[0]
print(df)
print(f"{len(df)} rows of turbine 1, step {step}, "
      f"{(df['power_kw'] * step / pd.Timedelta(hours=1)).sum() / 1000:.1f} MWh net")
