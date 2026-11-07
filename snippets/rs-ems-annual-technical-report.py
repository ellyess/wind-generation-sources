# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Serbia monthly wind production (GWh) for 2025 from the EMS annual technical report (PDF).

Section 1.4 has a chart table of production by month, with a wind row "ВЕ" (ветроелектране,
wind farms) holding twelve values, January to December. Traps handled:
- the table uses a comma for thousands and a point for decimals (the report's own footnote),
  the opposite of its running text ("1.384 GWh"), so commas are stripped;
- the 2025 report gives months in GWh; the 2023 report's monthly table is in MWh, and before
  2025 the row is labelled renewable production rather than wind, so this only reads 2025.
The figure is energy delivered into the transmission system, Serbia without Kosovo;
distribution-connected wind may be outside it.
"""

import io
import re

import pandas as pd
import pdfplumber
import requests

YEAR = 2025
URL = "https://ems.rs/wp-content/uploads/2026/07/GTI-2025.pdf"
WIND_ROW = re.compile(r"^ВЕ \([\d,]+%\)((?: [\d,]+){12})$")  # "ВЕ (4,18%) 109 152 ..."

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
    for page in pdf.pages:
        text = page.extract_text() or ""
        if f"Производња по месецима у {YEAR}" in text:  # "production by month in 2025"
            match = next(m for line in text.splitlines() if (m := WIND_ROW.match(line)))
            break

values = [float(v.replace(",", "")) for v in match.group(1).split()]
df = pd.DataFrame({"period": [f"{YEAR}-{m:02d}" for m in range(1, 13)],
                   "wind_gwh": values}).set_index("period")
print(df)
print(f"{len(df)} months, {df['wind_gwh'].sum():,.0f} GWh (the report's text gives 1,384)")
