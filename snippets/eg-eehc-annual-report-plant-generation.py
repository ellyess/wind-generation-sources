# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Egypt's grid wind generation (Zafarana), fiscal years 2001/02 to 2008/09, from EEHC's report.

Reads the "Total-Wind (Zafarana)" row of the table "Development of Gross Generated Energy (GWh)"
(PDF page 20) in the 2008/2009 annual report. Zafarana was then the only grid-connected wind
farm, so the row is both a plant and a national figure. Traps handled: years are Egyptian
fiscal years (1 July to 30 June), kept as printed ("08/09") and labelled by both calendar
years; recent reports (2022/23, 2024/25) are scanned images with no text layer, so this uses the
2008/2009 report, which still has one. Not handled: generated energy includes commissioning
tests, and the per-plant table of later reports mixes decimal points and commas.
"""

import io
import re

import pandas as pd
import pdfplumber
import requests

URL = "http://www.moee.gov.eg/english_new/EEHC_Rep/2008-2009en.pdf"  # the site serves http only
PAGE = 20

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
    text = pdf.pages[PAGE - 1].extract_text()
assert "Development of Gross Generated Energy (GWh)" in text
years = re.search(r"Comp\. Station((?: \d\d/\d\d)+)", text).group(1).split()
wind = re.search(r"Total-Wind \(Zafarana\)((?: \d+)+)", text).group(1).split()
assert len(years) == len(wind), (years, wind)

df = pd.DataFrame(
    {"fiscal_year": years, "wind_gwh": [float(v) for v in wind]},
    index=pd.Index([f"20{y[:2]}-07/20{y[3:]}-06" for y in years], name="period"),
)
print(df)
print(f"{len(df)} fiscal years, {df['wind_gwh'].sum():,.0f} GWh gross wind generation")
