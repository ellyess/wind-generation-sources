# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Monthly wind production on the Greek interconnected system for January to June 2026, from
DAPEEP's monthly bulletin of the renewables special account (June 2026 issue, version 1.0).

The bulletin's table "Εγκατεστημένη Ισχύς και Παραγωγή Μονάδων ΑΠΕ ΔΣ" gives, per month, the MW
and GWh of each technology; wind is Αιολικά. GWh are month totals; the MW column is the capacity
behind those figures. Traps handled: numbers are in the Greek format, a point for thousands and
a comma for decimals ("1.478" GWh is 1,478 GWh), so points are stripped and commas become
points; the table is found by its heading, not by page number. Not fixable in code: only farms
with an active DAPEEP support contract are counted (4,851 MW of 5,927 MW installed in June
2026), so these figures fall increasingly short of national wind output; bulletins are
reissued with new version numbers, so check the listing for a later version of a month.
"""

import io

import pandas as pd
import pdfplumber
import requests

URL = ("https://www.dapeep.gr/wp-content/uploads/2026/10/"
       "39_JUNE_2026_min_DELTIO_ELAPE_v_1.0_8.10.2026.pdf")
HEADING = "Εγκατεστημένη Ισχύς και Παραγωγή Μονάδων ΑΠΕ ΔΣ"  # interconnected system
MONTHS = ["Ιαν", "Φεβ", "Μαρ", "Απρ", "Μάι", "Ιουν", "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ"]

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
pdf = pdfplumber.open(io.BytesIO(resp.content))
page = next(p for p in pdf.pages if HEADING in (p.extract_text() or ""))
table = next(t for t in page.extract_tables() if t[0][:2] == ["Μήνας", "Αιολικά"])


def greek_number(text):
    return float(text.replace(".", "").replace(",", ".")) if text else None


rows = [r for r in table if r[0] and r[0].rstrip(" *") in MONTHS and r[2]]
df = pd.DataFrame(
    {"capacity_mw": [greek_number(r[1]) for r in rows],
     "wind_gwh": [greek_number(r[2]) for r in rows]},
    index=pd.PeriodIndex([f"2026-{MONTHS.index(r[0].rstrip(' *')) + 1:02d}" for r in rows],
                         freq="M", name="period"),
)
print(df)
print(f"{len(df)} months, {df['wind_gwh'].sum():,.0f} GWh "
      f"(the bulletin's year-to-date row: {table[-1][2]})")
