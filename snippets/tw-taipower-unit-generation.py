# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Taiwan wind power (MW) per farm, one real-time snapshot, from Taipower's unit generation file.

The real-time JSON (各機組發電量即時資訊) is overwritten every 10 minutes; it lists every unit,
own and purchased, with installed capacity and instantaneous net output in MW. Traps handled:
- the file starts with a UTF-8 byte-order mark, so it is decoded as utf-8-sig;
- values are instantaneous snapshots, not interval energy; time is the snapshot time;
- the stamp has no offset and Taipower states no zone, so it is kept as a naive `time`; Taiwan
  time (UTC+8, no daylight saving) matches the file's Last-Modified header but is not stated;
- the wind rows mix single farms, catch-all rows (其它台電自有, 其它購電風力) and a subtotal row
  (小計) with percentages inside its fields: the subtotal is dropped and used as a check;
- some farms show capacity "-" (footnote 10) while reporting output, read as missing; footnote
  marks such as "(註10)" are stripped from names, and the remarks column (部分檢修 partial
  maintenance, 通訊異常 communication fault) is kept.
There is no archive: harvest on a schedule. Onshore and offshore are not flagged.
"""

import json

import pandas as pd
import requests

URL = "https://service.taipower.com.tw/data/opendata/apply/file/d006001/001.json"

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
data = json.loads(resp.content.decode("utf-8-sig"))  # the file starts with a byte-order mark
rows = pd.DataFrame(data["aaData"])
rows = rows[rows["機組類型"] == "風力"]  # wind
subtotal = rows[rows["機組名稱"].str.startswith("小計")]
rows = rows.drop(subtotal.index)

stamp = pd.Timestamp(data["DateTime"])  # zone not stated
df = pd.DataFrame({
    "time": stamp,
    "unit_id": rows["機組名稱"].str.replace(r"\(註\d+\)", "", regex=True),
    "capacity_mw": pd.to_numeric(rows["裝置容量(MW)"], errors="coerce"),  # "-" -> NaN
    "wind_mw": pd.to_numeric(rows["淨發電量(MW)"]),
    "remark": rows["備註"].str.strip(),
}).set_index("time")
print(df)
check = float(subtotal["淨發電量(MW)"].iloc[0].split("(")[0])  # "2761.0(8.946%)"
print(f"{len(df)} wind rows, {df['wind_mw'].sum():,.1f} MW now (Taipower subtotal {check:,.1f} MW)")
