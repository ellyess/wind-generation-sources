# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Ten-minute active power of La Haute Borne turbine R80711, 2013 to 13 January 2018, from the
Mendeley Data re-deposit of ENGIE's open SCADA data (doi:10.17632/vmyg4yp3s8.2).

The 77 MB archive holds one CSV per turbine and filter version (F95, F99), so the snippet reads
only R80711's F99 file (10 MB compressed) out of it with HTTP range requests. P_avg is the
10-minute mean active power in kW. Traps handled: Date_time is French local time with an offset
that changes with daylight saving (+01:00, +02:00), so the offset is parsed and converted to
UTC rather than dropped. Whether a stamp opens or closes its 10 minutes is not stated, so stamps
are kept as published. Not fixable in code: the depositors removed about a fifth of the rows
(missing, corrupted, negative power), so the series cannot give energy totals or availability;
the F95 and F99 filters are not explained in the record. Use the coordinates in
static-information.csv (Meuse), not the place in the record's title.
"""

import io
import zipfile

import pandas as pd
import requests

URL = ("https://data.mendeley.com/public-files/datasets/vmyg4yp3s8/files/"
       "143e95a2-e5ee-4d58-b955-f825d1f2b78e/file_downloaded")
FILE = ("SCADA dataset of the Engie La Haute Borne wind farm _onshore_ in France/"
        "Cleaned data/Turbine_data_R80711_2013-2018_F99.csv")


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
    rows = pd.read_csv(f, usecols=["Date_time", "Wind_turbine_name", "P_avg"])

df = (
    rows.assign(time_utc=pd.to_datetime(rows["Date_time"], utc=True))  # offset -> UTC
    .rename(columns={"Wind_turbine_name": "unit_id", "P_avg": "power_kw"})
    .set_index("time_utc")
    .sort_index()[["unit_id", "power_kw"]]
)
print(df)
per_year = df.groupby(df.index.year).size()
print(f"{len(df)} 10-minutes kept ({per_year.loc[2014:2017].mean():.0f} a year of 52,560), "
      f"{df['power_kw'].sum() / 6 / 1000:.0f} MWh in the kept rows only")
