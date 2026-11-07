# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Luxembourg monthly wind production for one year, STATEC dataflow DF_A4102 (LUSTAT SDMX API).

Each value is the month's wind production in kilowatt-hours (UNIT_MEASURE KWH, multiplier 0),
labelled by month. Traps handled:
- values are kWh, not MWh, so they are divided by 1,000 here;
- the twelve months do not add up to STATEC's own annual wind generation (table DF_A4203), so
  the annual figure is fetched as well and the gap printed.
"""

import io

import pandas as pd
import requests

YEAR = "2024"
API = "https://lustat.statec.lu/rest/data/LU1,"


def sdmx(flow_and_key: str, start: str, end: str) -> pd.DataFrame:
    resp = requests.get(API + flow_and_key, timeout=60, params={
        "startPeriod": start, "endPeriod": end, "format": "csvfilewithlabels"})
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text))


# Key: unit KWH, measure PROD_EOL (wind production), monthly
rows = sdmx("DSD_NRG@DF_A4102,1.0/KWH.PROD_EOL.M...", f"{YEAR}-01", f"{YEAR}-12")
assert set(rows["UNIT_MEASURE"]) == {"KWH"} and set(rows["UNIT_MULT"]) == {0}
df = (
    rows.assign(wind_mwh=rows["OBS_VALUE"] / 1000)  # kWh -> MWh
    .rename(columns={"TIME_PERIOD": "period"})
    .set_index("period")
    .sort_index()[["wind_mwh"]]
)
annual = sdmx("DF_A4203,1.0/A.A03.SL04", YEAR, YEAR)["OBS_VALUE"].item()  # GWh, wind

print(df)
print(f"{len(df)} months, {df['wind_mwh'].sum() / 1000:.1f} GWh "
      f"(annual table DF_A4203: {annual:.1f} GWh)")
