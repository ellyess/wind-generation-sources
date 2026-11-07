# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual wind generation per APEC economy for one year from the APEC Energy Database (EGEDA).

The database is queried through its web form: a POST to electricity.php (the form's own target;
undocumented, no key or session) returns an HTML table headed "Unit:GWh" and a link to the same
table as a tab-separated text file, which is what this reads. Values are total power generation
(public producers plus autoproducers) in GWh for the year; whether a year is a calendar or fiscal
year is not stated.

Traps handled:
- A dash stands for both a reported zero and no data, so dashes are read as missing (NaN), not 0.
- The text file is a temporary copy made for each query, so it is fetched from the link in the
  response rather than from a fixed address.
"""

import re

import pandas as pd
import requests

YEAR = "2023"
BASE = "https://www.egeda.ewg.apec.org/egeda/database/"
ECONOMIES = ["001", "002", "003", "004", "005", "006", "007", "008", "009", "010", "011", "012",
             "013", "019", "014", "020", "015", "016", "017", "018", "021"]  # all 21, no total
FUELS = "&E=".join(["011000000", "011034000", "011034010", "011034311", "011034312", "011035000",
                    "011036000", "011024000", "011037000", "011037055", "011037052", "011037318",
                    "011037319", "011037320"])  # the form's hidden fuel list, as sent by the form

form = ([("Y1", YEAR)] + [("fC[]", c) for c in ECONOMIES]
        + [("fS[]", "003015000"), ("fE[]", FUELS), ("HEAD", "C"), ("ITEM", "S"), ("OIL", "0")])
page = requests.post(BASE + "php/electricity2/electricity.php", data=form, timeout=60)
page.raise_for_status()
txt = re.search(r"egeda/database/(tmp/[^\"]+\.txt)", page.text).group(1)
resp = requests.get(BASE + txt, timeout=60)
resp.raise_for_status()

lines = resp.text.splitlines()
economies = lines[2].split("\t")[2:]
wind = next(s for s in lines if s.startswith("\tWind\t")).split("\t")[2:]
df = (
    pd.DataFrame({"economy": economies, "wind_gwh": pd.to_numeric(wind, errors="coerce")})
    .assign(period=YEAR)
    .set_index("period")
)
assert lines[1].endswith("Unit:GWh")
print(df)
print(f"{len(df)} economies ({df['wind_gwh'].isna().sum()} dashes), "
      f"{df['wind_gwh'].sum() / 1000:.0f} TWh in {YEAR}")
