# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual wind net generation for every country from EIA's international bulk file (no key).

INTL.zip (about 24 MB, one JSON series per line) holds series INTL.37-12-<ISO3>-BKWH.A in
billion kWh, which equals TWh. The API v2 international route serves the same data but needs a
key; this file does not. Traps handled:
- "--" (not applicable, for example Germany before 1991 or successor states before 1992) and
  "ie" (French overseas departments from 2011, undefined in the file) are read as missing rather
  than failing the cast to numbers;
- regional aggregates (World, OECD, EU and so on) are separate series, and the WP<nn> series
  repeat single countries under another id; only series whose id carries the country's own code
  are kept, and World (INTL.37-12-WORL-BKWH.A) is used only for the check line.
Former states (East and West Germany, USSR, Yugoslavia) stay as their own rows.
"""

import io
import json
import zipfile

import pandas as pd
import requests

resp = requests.get("https://www.eia.gov/opendata/bulk/INTL.zip", timeout=180)
resp.raise_for_status()

records, world = [], None
with zipfile.ZipFile(io.BytesIO(resp.content)).open("INTL.txt") as lines:
    for line in lines:
        if b'"INTL.37-12-' not in line or b'-BKWH.A"' not in line:
            continue
        s = json.loads(line)
        code = s.get("series_id", "")[len("INTL.37-12-"):-len("-BKWH.A")]
        if not s.get("series_id", "").endswith("-BKWH.A") or code not in (s["geography"], "WORL"):
            continue
        series = pd.DataFrame(s["data"], columns=["period", "wind_twh"])
        series["wind_twh"] = pd.to_numeric(series["wind_twh"], errors="coerce")  # "--", "ie"
        if code == "WORL":
            world = series.set_index("period")["wind_twh"]
        else:
            records.append(series.assign(country=s["geography"]))

df = pd.concat(records).set_index("period").sort_index()[["country", "wind_twh"]]
print(df)
year = df.index.max()
print(f"{len(df)} country-years, {df['country'].nunique()} countries; {year}: "
      f"{df.loc[year, 'wind_twh'].sum():.0f} TWh summed, {world[year]:.0f} TWh World")
