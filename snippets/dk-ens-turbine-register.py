# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.2", "requests>=2.32"]
# ///
"""Monthly delivered output per Danish wind turbine from the Danish Energy Agency's register.

Reads "Vinddata 2026-09.xlsx" (one row per turbine, one column per month from 2023-01, in kWh)
and turns it long. It only downloads and reads the file: the agency's data policy forbids
altering its content, so nothing is re-saved. Traps handled: the header is on spreadsheet row 3;
numbers are text with comma decimals ("176804,75"); the media id changes with each refresh, so
the dated snapshot is pinned; turbines without published output (privately owned, and park
turbines since 2023, whose totals are in the separate Parkproduktion file) are dropped, so the
national sum is short. UTM x/y (ETRS89 metres) are kept as numbers, not lon/lat, with their
zone: 32N, except Bornholm rows whose x is in zone 33N, as the agency says Bornholm should be
(9 of its 36 are in 32N). In this snapshot the "Kommune" and "Type af placering" headers are
swapped, so LAND/HAV is read from "Kommune". Nine turbine numbers appear on two rows, and one
turbine's output is split across them, so output is summed per turbine and month.
"""

import io

import pandas as pd
import requests

URL = "https://ens.dk/media/8748/download"  # Vinddata (ultimo 09 2026), uploaded October 2026

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
wide = pd.read_excel(io.BytesIO(resp.content), header=2, dtype=str)  # header on row 3
wide.columns = wide.columns.str.strip()


def number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")


months = [c for c in wide.columns if c[:2] == "20"]
x = number(wide["UTM x-koordinat"])
bornholm = wide["Type af placering"].str.contains("Bornholm", na=False)  # the municipality
meta = pd.DataFrame({
    "unit_id": wide["Møllenummer (GSRN)"],
    "location": wide["Kommune"],  # LAND (onshore) or HAV (offshore) in this snapshot
    "capacity_kw": number(wide["Kapacitet (kW)"]),
    "utm_x": x,
    "utm_y": number(wide["UTM y-koordinat"]),
    "utm_zone": (32 + (bornholm & (x < 700_000))).where(x.notna()).astype("Int64"),
})
values = wide[months].apply(number)

df = (
    pd.concat([meta, values], axis=1)
    .melt(id_vars=list(meta.columns), var_name="period", value_name="wind_kwh")
    .dropna(subset=["wind_kwh"])
    .groupby(["period", *meta.columns], dropna=False)["wind_kwh"].sum()  # duplicate rows
    .reset_index(level=list(meta.columns))
    .sort_index()
)
print(df)
print(f"{len(df)} turbine-months, {df['unit_id'].nunique()} turbines with output, "
      f"{df['wind_kwh'].sum() / 1e6:.0f} GWh")
