# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Tunisia wind production (GWh) for August 2026, from two ONEM monthly energy bulletins (PDF).

Each bulletin's electricity production table has a row "EOLIENNE" (STEG's own wind farms):
full-year last year, then January-to-month totals for 2015, last year and this year, then two
percentages. Traps handled:
- figures are cumulative from January ("à fin août"), not single months, so the August value
  is the end-of-August total minus the end-of-July one;
- the table does not extract as a table (its cells are merged), so the wind line of the page
  text is read instead; the table groups thousands with a space, so the pattern accepts only
  four numbers of up to three digits and fails loudly otherwise;
- file names do not follow one pattern, so each bulletin's link is copied from the page.
Private wind, if any, would be in "Achat tiers", not in this row.
"""

import io
import re

import pandas as pd
import pdfplumber
import requests

BASE = "https://www.energiemines.gov.tn/fileadmin/docs-u1/"
BULLETINS = {"2026-07": "Conjoncture_%C3%A9nerg%C3%A9tique__fin_juillet_2026.pdf",
             "2026-08": "Conjoncture_%C3%A9nerg%C3%A9tique__Ao%C3%BBt__2026.pdf"}
WIND = re.compile(r"^EOLIENNE((?: \d{1,3}){4}) -?\d+% -?\d+%$")

ytd = {}
for period, name in BULLETINS.items():
    resp = requests.get(BASE + name, timeout=120)
    resp.raise_for_status()
    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    match = next(m for line in text.splitlines() if (m := WIND.match(line)))
    _, _, last_ytd, this_ytd = map(float, match.group(1).split())
    ytd[period] = {"wind_gwh_ytd": this_ytd, "wind_gwh_ytd_last_year": last_ytd}

df = pd.DataFrame(ytd).T.rename_axis("period")
df["wind_gwh"] = df["wind_gwh_ytd"].diff()  # single month from successive year-to-date totals
print(df)
print(f"{len(df)} bulletins, {df['wind_gwh'].iloc[-1]:.0f} GWh in August 2026 "
      f"(August 2025: {df['wind_gwh_ytd_last_year'].diff().iloc[-1]:.0f} GWh)")
