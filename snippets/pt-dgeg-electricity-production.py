# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32", "openpyxl>=3.1"]
# ///
"""Portuguese annual gross wind production by NUTS I region, DGEG workbook 2005-2025.

One sheet per region (Portugal, Continente, Açores, Madeira), "unidade: GWh", one column per
year; the wind row is "EÓLICA". Traps handled:
- the file link carries a random path segment and is replaced when DGEG updates it, so the
  link is read from the statistics page rather than hard-coded;
- the regions are kept apart and checked against the Portugal sheet, so the islands are not
  counted twice.
"""

import io
import re

import pandas as pd
import requests

PAGE = ("https://www.dgeg.gov.pt/pt/estatistica/energia/eletricidade/"
        "producao-anual-e-potencia-instalada/")
html = requests.get(PAGE, timeout=60).text
links = re.findall(r'href="(/media/[^"]+/dgeg-epa-2005-(\d{4})\.xlsx)"', html)
link = max(links, key=lambda m: m[1])[0]  # an older 2005-2022 file is listed too
xlsx = requests.get("https://www.dgeg.gov.pt" + link, timeout=120)
xlsx.raise_for_status()

frames = {}
for sheet, raw in pd.read_excel(io.BytesIO(xlsx.content), sheet_name=None, header=None).items():
    assert "unidade: GWh" in raw.iloc[6].astype(str).tolist()
    years = raw.iloc[7, 1:].astype(int).astype(str)
    wind = raw[raw[0].astype(str).str.strip() == "EÓLICA"].iloc[0, 1:]
    frames[sheet] = pd.Series(wind.to_numpy(dtype=float), index=years)

df = (
    pd.DataFrame(frames).rename_axis("period")
    .rename(columns={"Continente": "mainland", "Açores": "azores", "Madeira": "madeira",
                     "Portugal": "portugal"}).add_suffix("_gwh")
)
print(df.tail(6))
last = df.iloc[-1]
parts = last[["mainland_gwh", "azores_gwh", "madeira_gwh"]].sum()
print(f"{len(df)} years ({link.rsplit('/', 1)[-1]}); {df.index[-1]}: "
      f"{last['portugal_gwh']:,.0f} GWh Portugal, regions sum to {parts:,.0f}")
