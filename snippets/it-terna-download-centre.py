# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Italian national wind output per quarter hour for one month, Terna download centre.

The download centre's data service (undocumented: the JSON POST its own table makes) returns
net quarter-hourly production for one primary source. Terna states no unit, time zone or stamp
end; what follows is read from the data. Traps handled:
- values carry no unit; their size (0.12 to 7.0 in October 2026, for the national fleet, with
  a decimal comma on screen) only fits gigawatts, so they are read as GW and given in MW;
- stamps are .NET milliseconds since 0001-01-01 and behave as Italian wall-clock time (25
  October 2026 repeats 02:00 to 02:45), but Terna states no zone, so they are kept as a naive
  `time`, not UTC. The two copies of that hour come back in no reliable order, so they are
  dropped rather than guessed;
- a month runs 00:00 to 23:45, which fits period starts, but the stamp end is not stated;
- values are provisional until Terna's annual statistics, so keep the download date.
"""

import pandas as pd
import requests

YEAR, MONTH = "2026", "10"  # a month with the autumn clock change
body = {"filterDataset": "ActualGeneration", "filterType": "Wind", "filterYear": YEAR,
        "filterMonth": MONTH, "orderByColumn": "Date", "orderByDir": "asc",
        "pageSize": "5000", "pageIndex": "0", "db": "dati"}
resp = requests.post("https://dati.terna.it/api/sitecore/dati/downloadcenter/recordsv2",
                     json=body, timeout=60)
resp.raise_for_status()
js = resp.json()
rows = pd.DataFrame(js["Data"], columns=list(js["Columns"]))
assert len(rows) == js["Count"] and set(rows["Primary Source"]) == {"Wind"}

DOTNET_TO_UNIX_MS = 62_135_596_800_000  # 0001-01-01 to 1970-01-01
local = pd.to_datetime(rows["Date"] - DOTNET_TO_UNIX_MS, unit="ms")  # zone not stated
repeated = local.duplicated(keep=False)  # the autumn hour, in no reliable order
dropped = repeated.sum()
df = (
    rows.assign(time=local, wind_mw=rows["Actual Generation"] * 1000)[~repeated]
    .set_index("time")  # GW -> MW above
    .sort_index()[["wind_mw"]]
)
print(df)
print(f"{len(df)} quarter-hours ({dropped} repeated dropped), "
      f"{df['wind_mw'].sum() * 0.25 / 1e6:.2f} TWh")  # MW x 0.25 h
