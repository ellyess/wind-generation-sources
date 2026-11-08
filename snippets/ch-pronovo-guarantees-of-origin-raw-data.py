# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Monthly Swiss wind production from Pronovo's guarantee-of-origin raw data for 2025.

The 22 MB zip holds four quarterly CSVs, a ledger of every certificate transaction in the Swiss
registry. Swiss wind production is the "Issued(kWh)" quantity on rows for "Windenergie" produced
in Switzerland (Land "CH"), summed per production month and converted from kWh to MWh.
Traps handled:
- the ledger also holds cancellations, exports, expiries and certificates produced abroad, so
  only issued Swiss wind rows are kept;
- the files are Latin-1 with semicolons, and the header is not on the first line (the 2025 files
  start with an evaluation-date line and add an empty first column), so the header is found;
- month labels mix "1.2025" and "04.2025", so they are parsed as month and year.
Not handled by code: certificates for a month keep arriving for months afterwards and the file is
re-run under the same link, so a copy taken soon after year end is short.
"""

import io
import zipfile

import pandas as pd
import requests

URL = "https://pronovo.ch/?wpdmdl=16733"  # "HKN-Cockpit 2025 Rohdaten" on the reports page

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
parts = []
with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
    for name in sorted(n for n in zf.namelist() if n.endswith(".csv")):
        lines = zf.read(name).decode("latin-1").splitlines()
        start = next(i for i, line in enumerate(lines) if "Issued(kWh)" in line)
        keep = [lines[start]] + [line for line in lines[start + 1:] if ";Windenergie;CH;" in
                                 f";{line}"]
        parts.append(pd.read_csv(io.StringIO("\n".join(keep)), sep=";", dtype=str))
rows = pd.concat(parts)
rows = rows[(rows["Energieträger"] == "Windenergie") & (rows["Land"] == "CH")]

month = rows["Produktionsmonat"].str.split(".", expand=True).astype(int)
rows["period"] = [f"{y}-{m:02d}" for m, y in zip(month[0], month[1], strict=True)]
rows["wind_mwh"] = pd.to_numeric(rows["Issued(kWh)"]) / 1000
df = rows.groupby("period")[["wind_mwh"]].sum().round(1)
print(df)
print(f"{len(df)} months, {df['wind_mwh'].sum() / 1000:.1f} GWh issued for Swiss wind")
