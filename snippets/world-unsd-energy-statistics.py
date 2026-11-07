# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual wind electricity production by country from the UN Energy Statistics Database.

UNdata's CSV export for commodity EW gives "Electricity - total wind production" in "Kilowatt-
hours, million", which equals GWh, one value per country and year. The export comes from the
download handler under data.un.org/legacy/, which the legacy data page calls (undocumented; the
same handler at the site root now returns an HTML page). Traps handled:
- UNSD estimates are marked only by footnote 1 ("Estimate"); it is kept as an "estimate" column;
- the zipped CSV ends with a footnote table below a blank line, which is dropped;
- countries end in different years, so the check line counts the countries in each latest year.
"""

import io
import zipfile

import pandas as pd
import requests

resp = requests.get(
    "https://data.un.org/legacy/Handlers/DownloadHandler.ashx",
    params={"DataFilter": "cmID:EW", "DataMartId": "EDATA", "Format": "csv"},
    timeout=120,
)
resp.raise_for_status()
with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
    rows = pd.read_csv(z.open(z.namelist()[0]), dtype=str)
rows = rows[rows["Unit"] == "Kilowatt-hours, million"]  # drops the footnote table

df = (
    rows.assign(period=rows["Year"], wind_gwh=pd.to_numeric(rows["Quantity"]),
                estimate=rows["Quantity Footnotes"].eq("1"))
    .rename(columns={"Country or Area": "country"})
    .set_index("period")
    .sort_index()[["country", "wind_gwh", "estimate"]]
)
print(df)
last = df.reset_index().groupby("country")["period"].max().value_counts().sort_index()
print(f"{len(df)} country-years ({df['estimate'].sum()} estimates); 2023: "
      f"{df.loc['2023', 'wind_gwh'].sum() / 1000:.0f} TWh; countries ending in "
      + ", ".join(f"{year}: {n}" for year, n in last.tail(2).items()))
