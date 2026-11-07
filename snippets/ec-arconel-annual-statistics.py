# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pdfplumber>=0.11", "requests>=2.32"]
# ///
"""Ecuador's 2025 wind generation and capacity from ARCONEL's annual statistics (2025 edition).

Reads the "Eólica" row of Table 4, the national electricity balance (PDF page 19): nominal
capacity in MW (December 2025) and energy in GWh for 2025, each for the whole country and for
the national interconnected system (SNI), plus the energy delivered to public service. The PDF
is 47 MB. Traps handled: numbers use a comma decimal and a point for thousands ("185,82");
the national total (188.31 GWh) includes the isolated Galápagos systems, so the SNI column is
kept apart and the difference is shown. Percent columns are dropped.
"""

import io
import re

import pandas as pd
import pdfplumber
import requests

URL = "https://arconel.gob.ec/wp-content/uploads/downloads/2026/04/Estadistica-2025.pdf"
PAGE = 19

resp = requests.get(URL, timeout=300)
resp.raise_for_status()
with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
    text = pdf.pages[PAGE - 1].extract_text()
assert "Tabla Nro. 4: Balance nacional de energía eléctrica" in text
line = next(row for row in text.splitlines() if re.fullmatch(r"Eólica( [\d.,]+){10}", row))
nums = [float(v.replace(".", "").replace(",", ".")) for v in line.split()[1:]]
mw_all, _, mw_sni, _, gwh_all, _, gwh_sni, _, gwh_public, _ = nums  # value, share pairs

df = pd.DataFrame(
    {"capacity_mw": [mw_all, mw_sni], "wind_gwh": [gwh_all, gwh_sni],
     "delivered_public_gwh": [float("nan"), gwh_public]},
    index=pd.MultiIndex.from_tuples([("2025", "national"), ("2025", "SNI")],
                                    names=["period", "system"]),
)
print(df)
print(f"{len(df)} rows, {gwh_all:.2f} GWh national wind "
      f"({gwh_all - gwh_sni:.2f} GWh outside the SNI, mainly Galápagos)")
