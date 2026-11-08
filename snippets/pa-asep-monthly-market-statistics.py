# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Panama monthly wind generation per plant (MWh) from ASEP's market statistics PDF, August 2026.

Each month is one PDF at a fixed URL pattern (Spanish month name in capitals). Traps handled:
- wind plants are not in the main generation-by-plant table but in the "OTROS" breakdown on a
  later page, so every page is searched for rows whose technology is "Eólica";
- the breakdown table drops the technology column when extracted, so a table row is kept only
  when the page text has the same row with "Eólica" in front of it;
- values use a comma for thousands and a point for decimals;
- the September 2026 file repeats August's breakdown, so August 2026 is read instead; check that
  a month's breakdown adds up to its own "OTROS" total before trusting it.
Not handled: the plant list changes over time (before about 2021 the UEP complex at Penonomé is
a single "UEP" row; later UEP I and UEP II, then Toabré), and older files have another layout.
"""

import io

import pandas as pd
import pdfplumber
import requests

YEAR, MONTH, PERIOD = 2026, "AGOSTO", "2026-08"
URL = (f"https://www.asep.gob.pa/wp-content/uploads/electricidad/estadisticas_mensuales/"
       f"{YEAR}/{MONTH}_{YEAR}.pdf")

resp = requests.get(URL, timeout=120)
resp.raise_for_status()

records = []
with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
    for page in pdf.pages:
        lines = set((page.extract_text() or "").splitlines())
        for table in page.extract_tables():
            for row in table:
                if len(row) == 3 and f"Eólica {row[0]} {row[1]} {row[2]}" in lines:
                    records.append({"company": row[0], "unit_id": row[1],
                                    "wind_mwh": float(row[2].replace(",", ""))})

df = pd.DataFrame(records).assign(period=PERIOD).set_index("period")
print(df)
print(f"{len(df)} wind plants, {df['wind_mwh'].sum():,.0f} MWh in the month")
