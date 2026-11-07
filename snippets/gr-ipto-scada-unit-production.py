# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "python-calamine>=0.2", "requests>=2.32"]
# ///
"""Hourly output of each renewable station without a solar tag on the Greek interconnected
system for 10 January 2025, from IPTO's daily SystemRealizationSCADA file.

The file is found through the JSON listing that IPTO's market-statistics page calls (an
undocumented but public endpoint). Values are whole MWh per hour, labelled by hour columns 01 to
24, from non-certified SCADA data. Traps handled: stations are matched by name, not row
position, between the section heading (ΑΝΑΝΕΩΣΙΜΑ, or ΑΙΟΛΙΚΑ ΠΑΡΚΑ in older files) and its
total row; solar stations are dropped by their "(PV)" or "ΦΒ" tag. What is left is mostly wind
farms, but the file gives no technology, so some rows (named after substations, prefix ΚΥΤ)
may hold other renewables; check against a register before calling a row wind. Not fixable in
code: the file states no time zone and not which clock hour column 01 covers, so no UTC stamp
is built and df is indexed by the published hour label; the autumn clock-change day still has
24 columns, so one hour is missing or merged that day.
"""

import io

import pandas as pd
import requests

DAY = "2025-01-10"

listing = requests.get(
    "https://www.admie.gr/getOperationMarketFilewRange",
    params={"dateStart": DAY, "dateEnd": DAY, "FileCategory": "SystemRealizationSCADA"},
    timeout=60,
)
listing.raise_for_status()
xls = requests.get(listing.json()[0]["file_path"], timeout=60)
xls.raise_for_status()
sheet = pd.read_excel(io.BytesIO(xls.content), sheet_name="System_Production", header=None,
                      engine="calamine")

names = sheet[1].astype(str).str.strip()
start = names[names.isin(["ΑΝΑΝΕΩΣΙΜΑ", "ΑΙΟΛΙΚΑ ΠΑΡΚΑ"])].index[0]
end = names[names.isin(["TOTAL RES", "ΣΥΝΟΛΟ ΑΙΟΛΙΚΩΝ"])].index[0]
hours = [int(h) for h in sheet.loc[start, 2:25]]  # header row: 01 ... 24
section = sheet.loc[start + 1:end - 1].set_index(1).loc[:, 2:25].set_axis(hours, axis=1)
section = section[section.index.notna()]
stations = section[~section.index.str.contains(r"\(PV|ΦΒ", regex=True)]

df = (
    stations.rename_axis(index="unit_id", columns="hour")
    .stack()
    .astype(float)
    .rename("wind_mwh")
    .reset_index("unit_id")
    .sort_index(kind="stable")
)
print(df)
print(f"{len(df)} station-hours over {df['unit_id'].nunique()} stations, "
      f"{df['wind_mwh'].sum() / 1000:.1f} GWh (MWh per hour, so also average MW)")
