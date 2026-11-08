# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Wind output for one month in two Japanese supply areas, Kyushu and Hokkaido (エリア需給実績).

Since fiscal 2024 each operator publishes a monthly file, eria_jukyu_YYYYMM_NN.csv, with
30-minute values in average MW (単位[MW平均]); wind (風力発電実績) is after curtailment, and the
curtailed amount is a separate column (風力出力制御量). No time zone is stated, so stamps are
kept as a naive `time`, not UTC (Japan Standard Time, UTC+9, is likely but not stated). Traps
handled:
- files are Shift-JIS (cp932) with a units line above the header, which is skipped;
- the two operators label the half hour differently: Kyushu runs 0:30 to 24:00 (period end)
  and Hokkaido 00:00 to 23:30 (period start), observed in the files rather than documented, so
  Kyushu is moved back 30 minutes before the areas are stacked (a "24:00" label can only mark
  the end of a half hour, so the shift holds without documentation);
- dates and columns differ by operator ("20261001" against "2026/10/01", extra columns), so
  dates are parsed per file and columns picked by header name.
"""

import io

import pandas as pd
import requests

MONTH = "202610"
AREAS = {  # area: (URL, label marks the period end?)
    "kyushu": (f"https://www.kyuden.co.jp/td_area_jukyu/csv/eria_jukyu_{MONTH}_09.csv", True),
    "hokkaido": ("https://www.hepco.co.jp/network/con_service/public_document/"
                 f"supply_demand_results/csv/eria_jukyu_{MONTH}_01.csv", False),
}

frames = []
for area, (url, period_end) in AREAS.items():
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    rows = pd.read_csv(io.BytesIO(resp.content), encoding="cp932", skiprows=1, dtype=str)
    day = pd.to_datetime(rows["DATE"].str.replace("/", ""), format="%Y%m%d")
    hh, mm = rows["TIME"].str.split(":", expand=True).astype(int).T.values
    stamp = day + pd.to_timedelta(hh, unit="h") + pd.to_timedelta(mm, unit="min")  # 24:00 ok
    start = stamp - pd.Timedelta(minutes=30) if period_end else stamp
    frames.append(pd.DataFrame({
        "time": start,  # zone not stated
        "area": area,
        "wind_mw": rows["風力発電実績"].astype(float),
        "curtailed_mw": rows["風力出力制御量"].astype(float),
    }))

df = pd.concat(frames).set_index("time").sort_index()
print(df)
print(f"{len(df)} area half-hours, {df['wind_mw'].sum() * 0.5 / 1000:.1f} GWh")  # MW x 0.5 h
