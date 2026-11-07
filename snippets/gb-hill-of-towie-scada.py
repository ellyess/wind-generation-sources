# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Ten-minute active power of the 21 Hill of Towie turbines for June 2025, from the RES/TRIG
open dataset on Zenodo (version 2.1.0).

The yearly archives are about 1.5 GB, so the snippet reads one monthly table,
tblSCTurGrid_2025_06.csv (21 MB compressed), out of 2025.zip with HTTP range requests instead
of downloading the archive. wtc_ActPower_mean is the 10-minute mean active power in kW. Traps
handled: TimeStamp is in UTC and marks the end of the 10 minutes, so 10 minutes are subtracted
to stamp the start; StationId is mapped to turbine names (T01 = 2304510). Not handled: blade
upgrades (2021-2023) and the 2026 Dynamic Yaw trial change the power curve, so June 2025 is not
like for like with every other month.
"""

import io
import zipfile

import pandas as pd
import requests

URL = "https://zenodo.org/records/22662930/files/2025.zip"  # version 2.1.0


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
with archive.open("tblSCTurGrid_2025_06.csv") as f:
    rows = pd.read_csv(f, usecols=["TimeStamp", "StationId", "wtc_ActPower_mean"])

df = (
    rows.assign(
        time_utc=pd.to_datetime(rows["TimeStamp"]).dt.tz_localize("UTC") - pd.Timedelta("10min"),
        unit_id="T" + (rows["StationId"] - 2304509).astype(str).str.zfill(2),
    )
    .rename(columns={"wtc_ActPower_mean": "power_kw"})
    .set_index("time_utc")
    .sort_index()[["unit_id", "power_kw"]]
)
print(df)
mwh = df["power_kw"].sum() / 6 / 1000  # kW x 1/6 h -> kWh -> MWh
print(f"{len(df)} turbine-10-minutes over {df['unit_id'].nunique()} turbines, {mwh:.0f} MWh")
