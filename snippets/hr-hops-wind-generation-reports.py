# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32", "pdfplumber>=0.11"]
# ///
"""Croatian national wind production for one month, from HOPS's monthly report (PDF).

Each monthly report states the month's total production of all wind farms in MWh in its
running text, in Croatian and English side by side; there is no table of production. This
reads the May 2026 report and takes the figure from the English sentence ("Total wind power
plant generation in May 2026 was 273690.02 MWh"), checked against the Croatian one, which uses
a decimal comma. Traps handled:
- production is given only for Croatia as a whole: the farm table in the same report lists
  capacity and location, not output, so it is not read as per-farm generation;
- hourly output exists only as charts, so only the monthly total is taken.
"""

import io
import re

import pandas as pd
import pdfplumber
import requests

URL = ("https://www.hops.hr/page-file/zOzMS1Tyv4dK2LQH81KW4L/izvjestaji-o-proizvodnji-ve-u-rh/"
       "HOPS%20-%20Mjese%C4%8Dni%20izvje%C5%A1taj%20o%20proizvodnji%20VE%20u%20HR%20za%20"
       "Svibanj%202026.pdf")
resp = requests.get(URL, timeout=120)
resp.raise_for_status()
with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
    text = "\n".join(page.extract_text() or "" for page in pdf.pages[:12])

english = re.search(r"generation in (\w+) (\d{4}) was ([\d.]+)", text)
croatian = re.search(r"iznosila je ([\d.]*\d,\d+) MWh", text)  # first such sentence
month, year, mwh = english.groups()
assert float(croatian.group(1).replace(".", "").replace(",", ".")) == float(mwh)

period = pd.Period(f"{month} {year}", freq="M")
df = pd.DataFrame({"wind_mwh": [float(mwh)]}, index=pd.Index([str(period)], name="period"))
print(df)
print(f"{len(df)} month, {df['wind_mwh'].sum() / 1000:.1f} GWh")
