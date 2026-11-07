# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Ten-minute output of Penmanshiel turbine WT11 for the second half of 2016, from Cubico's
Penmanshiel wind farm data on Zenodo (version of August 2025, record 16807304).

The archives hold one CSV per turbine, so the snippet reads only WT11's 2016 file (11 MB
compressed) out of Penmanshiel_SCADA_2016_WT11-15_3107.zip with HTTP range requests. "Power
(kW)" is active power in kW and "Energy Export (kWh)" the energy in each 10 minutes. The headers
state UTC; they do not say whether a stamp opens or closes its 10 minutes, so stamps are kept as
published. Traps handled: the column header line starts with '#' like the nine comment lines
above it, so those nine lines are skipped instead of setting a comment character; repeated
timestamps keep the first row; the header claims 2016-01-01 onwards, but the data start on
2016-07-19 (the date in the file name), so the range comes from the rows. Not handled: there
is no WT03, and turbines 01 to 10 have no files for January 2023 or 2024, so a farm total
built from turbine files falls short there.
"""

import io
import zipfile

import pandas as pd
import requests

URL = "https://zenodo.org/records/16807304/files/Penmanshiel_SCADA_2016_WT11-15_3107.zip"
FILE = "Turbine_Data_Penmanshiel_11_2016-07-19_-_2017-01-01_1051.csv"


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


archive = zipfile.ZipFile(io.BufferedReader(HttpRange(URL), buffer_size=1 << 20))
with archive.open(FILE) as f:
    rows = pd.read_csv(f, skiprows=9,
                       usecols=["# Date and time", "Power (kW)", "Energy Export (kWh)"])

df = (
    rows.assign(time_utc=pd.to_datetime(rows["# Date and time"]).dt.tz_localize("UTC"))
    .drop_duplicates("time_utc", keep="first")
    .set_index("time_utc")
    .rename(columns={"Power (kW)": "power_kw", "Energy Export (kWh)": "energy_kwh"})
    [["power_kw", "energy_kwh"]]
)
print(df)
print(f"{len(df)} 10-minutes, {df['power_kw'].sum() / 6 / 1000:.0f} MWh from power "
      f"(kW x 1/6 h), {df['energy_kwh'].sum() / 1000:.0f} MWh exported")
