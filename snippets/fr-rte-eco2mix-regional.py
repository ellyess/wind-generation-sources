# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Wind output for the 12 mainland French regions for one day, from RTE's eCO2mix regional
consolidated data (via ODRE).

Half-hourly MW per region: eolien (combined), and from 2021 eolien_terrestre (onshore) and
eolien_offshore. RTE does not say whether a value is a mean or a snapshot, or whether the stamp
opens or closes the half hour, so stamps are kept as published (date_heure, in UTC). Traps
handled: eolien is a text field that can hold "ND", so it is cast to number with ND as missing;
on the March clock change the hour that did not exist copies the next hour under the same UTC
stamp, so duplicated stamps are dropped per region (on the October change one UTC hour simply
has no rows; leave it missing). The sample is 31 March 2024, which shows the copy. The data use
the export endpoint, not the paged API, which is capped at 50,000 calls a month.
"""

import pandas as pd
import requests

DAY = "2024-03-31"  # a French local date

resp = requests.get(
    "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "eco2mix-regional-cons-def/exports/json",
    params={"select": "date_heure,libelle_region,eolien,eolien_terrestre,eolien_offshore",
            "where": f"date='{DAY}'", "order_by": "date_heure"},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json())

df = (
    rows.assign(time_utc=pd.to_datetime(rows["date_heure"], utc=True),
                wind_mw=pd.to_numeric(rows["eolien"], errors="coerce"))  # "ND" -> NaN
    .rename(columns={"libelle_region": "region", "eolien_terrestre": "onshore_mw",
                     "eolien_offshore": "offshore_mw"})
    .drop_duplicates(["time_utc", "region"])
    .set_index("time_utc")
    .sort_index()[["region", "wind_mw", "onshore_mw", "offshore_mw"]]
)
print(df)
gwh = df["wind_mw"].sum() * 0.5 / 1000  # MW x 0.5 h, if each value is a half-hour mean
print(f"{len(df)} region-half-hours over {df['region'].nunique()} regions, about {gwh:.1f} GWh")
