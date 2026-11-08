# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Bulgarian hourly wind output for one day from ESO's "generation per day" page.

There is no file or API: the page embeds the day's chart data as JavaScript arrays, "xValues"
(UTC epoch milliseconds) and one array per fuel; wind is 'ВяЕЦ', in MW. Reading those arrays is
undocumented and will break if ESO changes the page script. ESO does not say whether a value is an
hourly mean or a reading, or whether a stamp starts its hour, so time_utc is each value's stamp
(the first is local midnight), not a claimed period start. The sample is 25 October 2026,
the autumn clock change, so the day has 25 hours.

Traps handled:
- On the autumn change day the page stamps two hours with the same instant and skips 00:00 UTC,
  so the stamps are not used as the index: values are taken in order and given consecutive hours
  from local midnight, after checking their count matches the hours in the local day.
- Wind is empty before 5 April 2021 (and 5 April has only 9 of 24 values) although other
  fuels are present; the snippet stops if the wind array is empty or short.
"""

import json
import re

import pandas as pd
import requests

DAY = "2026-10-25"  # a Bulgarian (Europe/Sofia) calendar day

date = pd.Timestamp(DAY).strftime("%d.%m.%Y")
resp = requests.get("https://www.eso.bg/doc/", params={"generation_per_day": "", "date": date},
                    timeout=60)
resp.raise_for_status()
page = resp.text
stamps = json.loads(re.search(r"var xValues = (\[[^\]]*\])", page).group(1))
wind = json.loads(re.search(r"name: 'ВяЕЦ', y: (\[[^\]]*\])", page).group(1))
assert wind and len(wind) == len(stamps), "no wind values for this day"

start = pd.Timestamp(DAY, tz="Europe/Sofia")
hours = int((start + pd.offsets.Day(1) - start) / pd.Timedelta("1h"))  # 23, 24 or 25
assert len(wind) == hours and pd.Timestamp(stamps[0], unit="ms", tz="UTC") == start
time_utc = pd.date_range(start.tz_convert("UTC"), periods=hours, freq="h", name="time_utc")

df = pd.DataFrame({"wind_mw": wind}, index=time_utc)
print(df)
print(f"{len(df)} hours ({len(set(stamps))} distinct stamps on the page), "
      f"{df['wind_mw'].sum() / 1000:.2f} GWh if each value is an hourly mean")
