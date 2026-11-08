# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32", "python-calamine>=0.2"]
# ///
"""Annual wind generation in Azerbaijan, from the State Statistical Committee's table 5.4.

Table 5.4, "Production of electricity, million kWh", has one row per year (1913 onwards) and a
"wind power plants" column from 2009. Million kWh are GWh, so no conversion is needed. Table 5.3
gives installed wind capacity at the end of each year, in MW, and is joined for a capacity
factor. Traps handled:
- cells hold "-" or "..." where there is no figure (the table gives no legend); both are read
  as missing, so 2011 and 2012, which are "-", drop out;
- year-end capacity overstates the fleet that ran all year when capacity jumps (2025: 64 MW to
  303.8 MW), so the capacity factor is shown against the previous year-end as well.
"""

import io

import pandas as pd
import requests

BASE = "https://www.stat.gov.az/source/balance_fuel/en/"


def table(name: str, keyword: str) -> pd.Series:
    raw = requests.get(BASE + name, timeout=60)
    raw.raise_for_status()
    sheet = pd.read_excel(io.BytesIO(raw.content), header=None, engine="calamine")
    col = next(c for c in sheet.columns
               if sheet[c].astype(str).str.contains(keyword, case=False).any())
    years = pd.to_numeric(sheet[1], errors="coerce")
    rows = years.between(1900, 2100)
    values = pd.to_numeric(sheet.loc[rows, col], errors="coerce")  # "-" and "..." -> missing
    return pd.Series(values.values, index=years[rows].astype(int).astype(str))


wind = table("005_4en.xls", "wind power")  # million kWh
capacity = table("005_3en.xls", "wind power")  # MW at year end
df = pd.DataFrame({"wind_gwh": wind, "capacity_mw": capacity})
df["cf_year_end"] = (df["wind_gwh"] * 1000 / (df["capacity_mw"] * 8760)).round(3)
df["cf_previous_end"] = (df["wind_gwh"] * 1000
                         / (df["capacity_mw"].shift(1) * 8760)).round(3)
df = df.dropna(subset=["wind_gwh"])
df.index.name = "period"
print(df)
print(f"{len(df)} years, {df['wind_gwh'].sum():.1f} GWh in all; "
      f"{df.index[-1]}: {df['wind_gwh'].iloc[-1]} GWh")
