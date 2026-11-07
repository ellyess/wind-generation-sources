# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Monthly wind generation for Canada and each province and territory, from Statistics Canada.

Table 25-10-0015-01 gives electricity generation by type in megawatt hours per reference month.
The whole table is a 1 MB zipped CSV; this keeps "Wind power turbine" for all classes of
producer and one year. Traps handled: cells that are not available ("..") or suppressed for
confidentiality ("x") have an empty value and are kept as missing, with the STATUS column, not
read as zero (British Columbia has no wind rows at all before 2016, so pick a year from 2016
to compare provinces); the national row (Canada) is kept separate from the provinces so it is
not added twice. Not handled by code: the survey grew from about 400 to about 1,200 companies
in January 2016, so do not read the 2015-2016 step as new build; revised months carry an "r"
symbol.
"""

import io
import zipfile

import pandas as pd
import requests

YEAR = "2025"

resp = requests.get("https://www150.statcan.gc.ca/n1/tbl/csv/25100015-eng.zip", timeout=120)
resp.raise_for_status()
with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
    rows = pd.read_csv(zf.open("25100015.csv"), encoding="utf-8-sig", dtype={"STATUS": str})

rows = rows[(rows["Type of electricity generation"] == "Wind power turbine")
            & (rows["Class of electricity producer"] == "Total all classes of electricity producer")
            & rows["REF_DATE"].str.startswith(YEAR)]
assert (rows["UOM"] == "Megawatt hours").all() and (rows["SCALAR_FACTOR"] == "units").all()

df = (
    rows.rename(columns={"REF_DATE": "period", "GEO": "geo", "VALUE": "wind_mwh",
                         "STATUS": "status"})
    .set_index("period")
    .sort_index()[["geo", "wind_mwh", "status"]]
)
print(df)
canada = df.loc[df["geo"] == "Canada", "wind_mwh"]
print(f"{len(df)} rows, {df['wind_mwh'].isna().sum()} not available; Canada {YEAR}: "
      f"{canada.sum() / 1e6:.1f} TWh over {canada.count()} months")
