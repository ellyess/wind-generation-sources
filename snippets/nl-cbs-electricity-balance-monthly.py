# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Netherlands monthly wind production, onshore and offshore, for one year from CBS table 84575NED.

Net production in million kWh (GWh) per month, from the CBS OData API. Traps handled:
- the table mixes monthly, quarterly and yearly rows, so only period codes with "MM" are kept;
- empty cells mean not published (wind before 2002, offshore before October 2006), so they stay
  missing rather than zero.
Recent years are provisional and revised for up to two years; record the download date.
"""

import pandas as pd
import requests

YEAR = 2025
COLUMNS = {"WindenergieOpLand_13": "onshore_gwh", "WindenergieOpZee_14": "offshore_gwh",
           "WindenergieTotaal_12": "wind_gwh"}

resp = requests.get(
    "https://opendata.cbs.nl/ODataApi/odata/84575NED/TypedDataSet",
    params={"$filter": f"startswith(Perioden,'{YEAR}MM')",
            "$select": "Perioden," + ",".join(COLUMNS)},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["value"])
rows = rows[rows["Perioden"].str.contains("MM")]  # monthly rows only

df = (
    rows.assign(period=rows["Perioden"].str.replace("MM", "-"))  # 2025MM08 -> 2025-08
    .set_index("period")
    .rename(columns=COLUMNS)[list(COLUMNS.values())]
)
print(df)
print(f"{len(df)} months, {df['wind_gwh'].sum():,.0f} GWh "
      f"({df['onshore_gwh'].sum():,.0f} onshore, {df['offshore_gwh'].sum():,.0f} offshore)")
