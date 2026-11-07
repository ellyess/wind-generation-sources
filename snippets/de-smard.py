# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""German onshore and offshore wind for one day from SMARD's chart data (Bundesnetzagentur).

Uses the JSON files the SMARD charts load (undocumented by the publisher; see bundesAPI/smard-api):
one file per filter, region and week, named by the week's first stamp. Filter 4067 is wind
onshore, 1225 wind offshore. Stamps are Unix milliseconds at the start of each quarter hour.
Traps handled: values are energy per quarter hour (MWh), not MW, so wind_mw is MWh x 4; the
sample is the October clock-change day (100 quarter hours), where the epoch stamps stay unique
although the CSV export repeats the 02:00 clock times.
"""

import pandas as pd
import requests

WEEK = 1760911200000  # Monday 2025-10-20 00:00 Berlin, read from index_quarterhour.json
DAY = "2025-10-26"  # local day of the October clock change


def series(filter_id: int) -> pd.Series:
    url = f"https://www.smard.de/app/chart_data/{filter_id}/DE/{filter_id}_DE_quarterhour_{WEEK}.json"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    s = pd.DataFrame(resp.json()["series"], columns=["ms", "mwh"]).set_index("ms")["mwh"]
    s.index = pd.to_datetime(s.index, unit="ms", utc=True)
    return s


df = pd.DataFrame({"onshore_wind_mwh": series(4067), "offshore_wind_mwh": series(1225)})
df.index.name = "time_utc"
df = df[df.index.tz_convert("Europe/Berlin").strftime("%Y-%m-%d") == DAY]
df["wind_mw"] = (df["onshore_wind_mwh"] + df["offshore_wind_mwh"]) * 4  # MWh per 15 min -> MW
print(df)
total = df["onshore_wind_mwh"].sum() + df["offshore_wind_mwh"].sum()
print(f"{len(df)} quarter hours, {total / 1000:.1f} GWh")
