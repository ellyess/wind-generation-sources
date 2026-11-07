# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Monthly EEG-paid wind volumes per installation, 50Hertz area, 2025, from netztransparenz.de.

The EEG movement data list every installation paid under the Renewable Energy Sources Act, with
the volume (Strommenge) and payments; wind rows have a remuneration category starting with "W".
One zip per transmission operator; the 50Hertz one is the smallest (18 MB, two CSVs of about
75 MB each). Traps handled: the Monat column is 1 to 12 for a month and 0 for an annual value,
so month-0 rows get the period "2025" and are not read as January; the CSVs are UTF-8 with a BOM,
";" separators and comma decimals; only the latest year stays online, so this link will expire.
The unit of Strommenge is not stated; it is read as kWh, as the payments per unit suggest.
"""

import io
import zipfile

import pandas as pd
import requests

URL = ("https://www.netztransparenz.de/cdn/files/0687a707-cf7c-45c1-29cf-08defc51206b/"
       "50hertz%20transmission%20gmbh%20eeg-zahlungen%20bewegungsdaten%202025.zip")
YEAR = 2025
COLS = ["EEG_Mastr_Nr", "Verguetungskategorie", "Strommenge", "Monat"]

resp = requests.get(URL, timeout=300)
resp.raise_for_status()
with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
    parts = [pd.read_csv(z.open(n), sep=";", decimal=",", encoding="utf-8-sig", usecols=COLS)
             for n in z.namelist() if n.endswith(".csv")]
rows = pd.concat(parts, ignore_index=True)
wind = rows[rows["Verguetungskategorie"].str.startswith("W")]

df = (
    wind.assign(period=[f"{YEAR}-{m:02d}" if m else str(YEAR) for m in wind["Monat"]])
    .rename(columns={"EEG_Mastr_Nr": "unit_id", "Verguetungskategorie": "category",
                     "Strommenge": "wind_kwh"})
    .set_index("period")
    .sort_index()[["unit_id", "category", "wind_kwh"]]
)
print(df)
annual = df.loc[df.index == str(YEAR), "wind_kwh"].sum()
print(f"{len(df)} rows, {df['unit_id'].nunique()} wind installations, "
      f"{df['wind_kwh'].sum() / 1e9:.2f} TWh ({annual / 1e9:.2f} TWh in annual rows)")
