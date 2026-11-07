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
- stamps are .NET milliseconds since 0001-01-01 in Italian wall-clock time: 25 October 2026
  repeats 02:00 to 02:45. They are converted from Europe/Rome to UTC. The two copies of that
  hour come back in no reliable order, so they are dropped rather than guessed;
- a month runs 00:00 to 23:45, so stamps are read as period starts;
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
local = pd.to_datetime(rows["Date"] - DOTNET_TO_UNIX_MS, unit="ms")
utc = local.dt.tz_localize("Europe/Rome", ambiguous="NaT", nonexistent="NaT")
dropped = utc.isna().sum()
df = (
    rows.assign(time_utc=utc.dt.tz_convert("UTC"), wind_mw=rows["Actual Generation"] * 1000)
    .dropna(subset=["time_utc"])  # GW -> MW above
    .set_index("time_utc")
    .sort_index()[["wind_mw"]]
)
print(df)
print(f"{len(df)} quarter-hours ({dropped} ambiguous dropped), "
      f"{df['wind_mw'].sum() * 0.25 / 1e6:.2f} TWh")  # MW x 0.25 h
