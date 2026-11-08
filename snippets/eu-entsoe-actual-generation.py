# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Belgian wind output for one day from ENTSO-E's Actual Generation per Production Type (16.1.B&C).

Each value is MW ("MAW") over its interval. Stamps are UTC: each Period gives a start and a
resolution, and a point's time is start + resolution x (position - 1), the start of its interval.
The day asked for is the Belgian clock-change day, 25 local hours.

Traps handled:
- Onshore (B19) and offshore (B18) wind are separate series; both are kept and added.
- Offshore can carry consumption beside generation; only series with an inBiddingZone (generation)
  are kept, and those with an outBiddingZone (consumption) are dropped.
- Variable-sized blocks (curveType A03) leave out positions where the value does not change, so
  each series is filled forward to every interval of its Period.
- The day is given in UTC, so the local clock change is handled by asking 22:00Z to 23:00Z.
"""
# wgs: needs ENTSOE_API_KEY

import os
import xml.etree.ElementTree as ET

import pandas as pd
import requests

AREA = "10YBE----------2"  # Belgium
START, END = "202410262200", "202410272300"  # 27 October 2024 in Brussels time, in UTC

try:
    resp = requests.get("https://web-api.tp.entsoe.eu/api", timeout=120, params={
        "documentType": "A75", "processType": "A16", "in_Domain": AREA,
        "periodStart": START, "periodEnd": END, "securityToken": os.environ["ENTSOE_API_KEY"]})
except requests.RequestException as err:  # the message would carry the key in the URL
    raise SystemExit(f"request failed: {type(err).__name__}") from None
if resp.status_code != 200:
    try:  # errors come as an Acknowledgement document; report its reason on one line
        reason = ET.fromstring(resp.content).findtext(".//{*}Reason/{*}text")
    except ET.ParseError:
        reason = None
    raise SystemExit(f"HTTP {resp.status_code}: {reason or resp.reason}")

root = ET.fromstring(resp.content)
ns = {"g": root.tag.split("}")[0].strip("{")}  # the document's own namespace
TYPES = {"B19": "onshore_mw", "B18": "offshore_mw"}
series = {}
for ts in root.iterfind("g:TimeSeries", ns):
    psr = ts.findtext("g:MktPSRType/g:psrType", namespaces=ns)
    if psr not in TYPES or ts.find("g:inBiddingZone_Domain.mRID", ns) is None:
        continue  # not wind, or a consumption series
    for period in ts.iterfind("g:Period", ns):
        start = pd.Timestamp(period.findtext("g:timeInterval/g:start", namespaces=ns))
        end = pd.Timestamp(period.findtext("g:timeInterval/g:end", namespaces=ns))
        step = pd.Timedelta(period.findtext("g:resolution", namespaces=ns))
        pts = {int(p.findtext("g:position", namespaces=ns)): float(p.findtext("g:quantity",
               namespaces=ns)) for p in period.iterfind("g:Point", ns)}
        n = int((end - start) / step)
        values = pd.Series(pts).reindex(range(1, n + 1)).ffill()  # A03 blocks run on
        values.index = start + step * (values.index - 1)
        series[TYPES[psr]] = pd.concat([series.get(TYPES[psr]), values])

df = pd.DataFrame(series).rename_axis("time_utc").sort_index()
df["wind_mw"] = df.sum(axis=1)
print(df)
print(f"{len(df)} intervals, mean {df['wind_mw'].mean():,.0f} MW, "
      f"peak {df['wind_mw'].max():,.0f} MW")  # MW, not energy: the value type is not stated
