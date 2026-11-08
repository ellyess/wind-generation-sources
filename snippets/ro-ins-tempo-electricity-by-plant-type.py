# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual wind generation in Romania, from INS TEMPO-Online matrix IND118A.

The matrix endpoint lists each dimension with numeric codes; a POST to the pivot endpoint with
one code list per dimension returns comma-separated text. The snippet looks up the wind category
("Eoliana") and every year by name, asks for all years, and reads the values in million kWh,
which are GWh. Traps handled:
- codes are looked up from the matrix rather than hard-coded, apart from the dimension order;
- wind has no rows before 2007, so the years returned are printed rather than assumed;
- labels such as "Anul 2024" are turned into a plain year.
The service is plain HTTP on port 8077.
"""

import io

import pandas as pd
import requests

BASE = "http://statistici.insse.ro:8077/tempo-ins"

matrix = requests.get(f"{BASE}/matrix/IND118A", timeout=60)
matrix.raise_for_status()
dims = matrix.json()["dimensionsMap"]
category, years, unit = (d["options"] for d in dims)
wind = next(o["nomItemId"] for o in category if o["label"] == "Eoliana")
assert unit[0]["label"] == "Milioane kilowatti-ora"
query = ":".join([str(wind), ",".join(str(o["nomItemId"]) for o in years),
                  str(unit[0]["nomItemId"])])
resp = requests.post(f"{BASE}/pivot", timeout=60, json={
    "encQuery": query, "language": "ro", "matCode": "IND118A", "matMaxDim": 3,
    "matRegJ": 0, "matUMSpec": 0})
resp.raise_for_status()

rows = pd.read_csv(io.StringIO(resp.text), skipinitialspace=True)
rows.columns = ["category", "year", "unit", "wind_gwh"]
df = rows.assign(period=rows["year"].str.removeprefix("Anul ")).set_index("period")[["wind_gwh"]]
print(df)
print(f"{len(df)} years ({df.index[0]} to {df.index[-1]}), {df['wind_gwh'].sum():,} GWh in all")
