# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Monthly wind production of the Federation of Bosnia and Herzegovina from one FZS release.

Each monthly PDF release (here April 2025, release 22.2.4) has an electricity table in GWh with
two months of the previous and current year and both years to date. The wind row is
"Vjetroelektrane" ("Wind energy"); its first occurrence is gross production (wind own consumption
is reported as nil, so net is the same).

Traps handled:
- Numbers use a dot as thousands separator ("2.794" is 2,794 GWh).
- The latest month is a first result that becomes final with the next month's release, so it is
  flagged "first"; the other months in the table are final.
- The release covers the Federation only, one entity of Bosnia and Herzegovina, not the country.
"""

import io
import re

import pandas as pd
import pdfplumber
import requests

URL = "https://fzs.ba/wp-content/uploads/2025/05/22.2.4.pdf"  # April 2025 release
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

resp = requests.get(URL, timeout=60)
resp.raise_for_status()
with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
    text = next(p.extract_text() for p in pdf.pages if "Vjetroelektrane" in p.extract_text())
lines = text.splitlines()

years = re.findall(r"\b20\d\d\b", next(s for s in lines if re.fullmatch(r"[\d ]+", s)))
months = next(s for s in lines if re.fullmatch(r"[IVX\- ]+", s)).split()  # III IV III IV I-IV ..
wind = next(s for s in lines if s.startswith("Vjetroelektrane"))  # first one is gross
values = [float(v.replace(".", "")) for v in re.findall(r"[\d.]+", wind)]

monthly = [m for m in months if "-" not in m]  # each year heads two month columns
periods = [f"{years[i // 2]}-{ROMAN.index(m) + 1:02d}" for i, m in enumerate(monthly)]
df = (
    pd.DataFrame({"period": periods, "wind_gwh": values[: len(periods)]})
    .set_index("period")
    .sort_index()
)
df["status"] = "final"
df.loc[df.index.max(), "status"] = "first"  # final once the next release is out
print(df)
print(f"{len(df)} months, {df['wind_gwh'].sum():.0f} GWh "
      f"(year to date in the release: {values[len(periods):]} GWh)")
