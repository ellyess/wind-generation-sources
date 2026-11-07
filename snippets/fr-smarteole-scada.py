# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""One-minute active power of the seven SMARTEOLE turbines (SMV1 to SMV7) for 18 February 2020,
from the SMARTEOLE wind farm control open dataset on Zenodo (doi:10.5281/zenodo.7342466).

The 150 MB archive holds the SCADA as one wide CSV (70 MB compressed), so the snippet streams
only its first 3,000 rows out of the archive with HTTP range requests. active_power_N_avg is the
one-minute mean for turbine N. The unit is not stated; values near 2,000 on 2.05 MW turbines
read as kW. The time zone and which end of the minute the stamp marks are not stated either. The
stamps run straight through 02:00 to 02:59 on 29 March 2020, an hour that did not exist on
French clocks, so they are not French local time; they are read as UTC here, as RES's wind-up
tool also reads them, which is an assumption (CET all year would fit too). Not fixable in code:
minutes when any turbine was stopped were removed, so the series cannot give energy totals, and
SMV6 was deliberately yawed off the wind at times (see the control log), so its output and its
neighbours' are not normal operation.
"""

import io
import zipfile

import pandas as pd
import requests

URL = "https://zenodo.org/records/7342466/files/SMARTEOLE-WFC-open-dataset.zip"
FILE = "SMARTEOLE-WFC-open-dataset/SMARTEOLE_WakeSteering_SCADA_1minData.csv"
COLS = {f"active_power_{n}_avg": f"SMV{n}" for n in range(1, 8)}


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
    rows = pd.read_csv(f, usecols=["time", *COLS], nrows=3000)  # from 17 Feb 16:30

df = (
    rows.assign(time_utc=pd.to_datetime(rows["time"]).dt.tz_localize("UTC"))  # assumed
    .set_index("time_utc")
    .loc["2020-02-18", list(COLS)]
    .rename(columns=COLS)
    .rename_axis(columns="unit_id")
    .stack()
    .rename("power_kw")
    .reset_index("unit_id")
)
print(df)
print(f"{len(df)} turbine-minutes over {df['unit_id'].nunique()} turbines, "
      f"{df['power_kw'].sum() / 60 / 1000:.0f} MWh in the minutes kept")  # kW x 1/60 h
