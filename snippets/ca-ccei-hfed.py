# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Alberta wind output for one day from Statistics Canada's High-Frequency Electricity Data API.

HFED scrapes provincial sites; for Alberta it holds a reading about every 5 minutes, in MW.
Traps handled: only FREQ "N" rows are kept, because the "H" rows (to August 2024) repeat the
reading at each hour mark; the request runs a day past the wanted day, because endPeriod drops
readings after 23:00 of its last day; CCEI does not state TIME_PERIOD's zone, so it is kept as a
naive `time` (the local-time column and Ontario's match with IESO suggest UTC) and
DATETIME_LOCAL_OFFSET is ignored. Whether a value is a snapshot or a mean, and which end of a
period a stamp marks, are not stated, so no energy total is printed.
"""

import io

import pandas as pd
import requests

DAY = "2024-01-15"
URL = "https://api.statcan.gc.ca/hfed-dehf/sdmx/rest/data/CCEI,DF_HFED_AB,1.0/N...WIND"
end = (pd.Timestamp(DAY) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

resp = requests.get(
    URL,
    params={"startPeriod": DAY, "endPeriod": end, "dimensionAtObservation": "AllDimensions",
            "format": "csv"},
    timeout=120,
)
resp.raise_for_status()
rows = pd.read_csv(io.StringIO(resp.text))
assert set(rows["UNIT_MEASURE"]) == {"MW"}

df = (
    rows[rows["FREQ"] == "N"]
    .assign(time=lambda d: pd.to_datetime(d["TIME_PERIOD"]))  # zone not stated
    .drop_duplicates("time")
    .set_index("time")
    .sort_index()[["OBS_VALUE"]]
    .rename(columns={"OBS_VALUE": "wind_mw"})
)
df = df[df.index.strftime("%Y-%m-%d") == DAY]
print(df)
print(f"{len(df)} readings (288 for a full day), mean {df['wind_mw'].mean():.0f} MW")
