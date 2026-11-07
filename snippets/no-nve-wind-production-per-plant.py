# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Norway hourly wind production per plant for one day from NVE's 2002-2021 file.

One 22 MB xlsx: a row of plant names (kraftverknavn), a row of plant numbers (kraftverknr),
then one row per hour with a value per plant. Traps handled:
- stamps are UTC+1 all year, as the file name says, not Norwegian local time, so one hour is
  subtracted to reach UTC (no daylight saving shift);
- the wide sheet is turned long, one row per plant and hour, keyed on the plant number;
- empty cells (a plant not yet built) are dropped, not read as zero.
NVE states no unit and not which end of the hour a stamp marks. This assumes MWh per hour
(Kvitfjell, about 200 MW, peaks near 130) stamped at the hour start, as the entry's trap does
(the file's last stamp, 23:00 UTC+1 on 31 December 2021, leaves the 23:00 UTC hour missing).
"""

import io

import openpyxl
import pandas as pd
import requests

DAY = pd.Timestamp("2021-01-15")  # a UTC+1 date
URL = "https://www.nve.no/media/13399/vindprod2002-2021_kraftverk_utcplus1.xlsx"

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
sheet = openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True).worksheets[0]

rows = sheet.iter_rows(values_only=True)
names, numbers, _ = next(rows), next(rows), next(rows)  # name row, number row, "timestamp"
records = []
for row in rows:
    stamp = pd.Timestamp(row[0])
    if stamp.normalize() > DAY:
        break  # rows are in time order
    if stamp.normalize() == DAY:
        records += [(stamp, numbers[j], names[j].strip(), v)
                    for j, v in enumerate(row[1:], 1) if v is not None]

rows = pd.DataFrame(records, columns=["utc_plus1", "unit_id", "name", "wind_mwh"])
df = (
    rows.assign(time_utc=(rows["utc_plus1"] - pd.Timedelta(hours=1)).dt.tz_localize("UTC"))
    .set_index("time_utc")
    .sort_index()[["unit_id", "name", "wind_mwh"]]
)
print(df)
print(f"{len(df)} plant-hours, {df['unit_id'].nunique()} plants, {df['wind_mwh'].sum():,.0f} MWh")
