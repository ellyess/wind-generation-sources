# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Ten-minute output of turbine WT01 for January 2020, from the UNDERPIN six-month monitoring
dataset of a 10-turbine onshore wind farm in Greece (Zenodo record 14546480).

The data are one 181 MB xlsx workbook with a sheet per turbine. An xlsx is a zip archive, so
the snippet opens it with HTTP range requests and reads only the first 4,464 rows (31 days) of
sheet WT01_data.csv, about 24 MB of transfer. Traps handled: 'Grid Production Power Avg. [W]'
and the possible-power column are labelled in watts but hold kilowatts (they peak near 3,001 on
turbines of about 3 MW), so they are read as kW. Not fixable in code: the time zone is not
stated, so the stamps are left as published, without a zone (the index is "time", not
"time_utc"). They form an unbroken 10-minute grid through 29 March 2020, so they are not Greek
wall-clock time, but UTC and fixed UTC+2 both fit. Which end of the 10 minutes a stamp marks is
not stated either.
"""

import io

import pandas as pd
import requests

URL = "https://zenodo.org/records/14546480/files/SCADA__monitoring_dataset_2020.xlsx"
COLS = {"Grid Production Power Avg. [W]": "power_kw",  # labelled W, values are kW
        "Grid Production PossiblePower Avg. [W]": "possible_kw"}


class HttpRange(io.RawIOBase):
    """A seekable, read-only view of a remote file, fetched in pieces by HTTP range requests."""

    def __init__(self, url):
        self.url, self.pos = url, 0
        head = requests.head(url, allow_redirects=True, timeout=60)
        self.url, self.size = head.url, int(head.headers["Content-Length"])

    def readable(self):
        return True

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.pos = (offset, self.pos + offset, self.size + offset)[whence]
        return self.pos

    def readinto(self, buf):
        end = min(self.pos + len(buf), self.size)
        if end <= self.pos:
            return 0
        r = requests.get(self.url, headers={"Range": f"bytes={self.pos}-{end - 1}"}, timeout=60)
        r.raise_for_status()
        buf[: len(r.content)] = r.content
        self.pos += len(r.content)
        return len(r.content)


workbook = io.BufferedReader(HttpRange(URL), buffer_size=1 << 20)
rows = pd.read_excel(workbook, sheet_name="WT01_data.csv", usecols=["Timestamp", *COLS],
                     nrows=31 * 144, engine="openpyxl")

df = (
    rows.assign(time=pd.to_datetime(rows["Timestamp"]), unit_id="WT01")
    .set_index("time")
    .rename(columns=COLS)[["unit_id", "power_kw", "possible_kw"]]
)
print(df)
mwh = df["power_kw"].sum() / 6 / 1000  # kW x 1/6 h -> kWh -> MWh
print(f"{len(df)} 10-minutes, {mwh:.0f} MWh (possible {df['possible_kw'].sum() / 6000:.0f} MWh)")
