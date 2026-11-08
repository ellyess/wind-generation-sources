# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Nicaragua hourly wind energy per unit for one day from CNDC's post-dispatch (Postdespacho).

Uses the undocumented JSON endpoint that the MEMN Diarios page itself calls; the date is
dd/mm/yyyy. Values are MWh per hour per generating unit. Traps handled:
- there is no technology field, so wind units are picked by code: AMY1 and AMY2 (Amayo),
  EOL (Eolo), PBP (Blue Power) and ABR (agent PCG-ABR; CNDC does not label it wind);
- "valor" is text and may use a decimal comma, so a comma is replaced before parsing;
- some days return only the demand rows, so an empty wind set stops the script rather than
  reading as zero.
CNDC states neither the time zone nor which end of the hour "00" to "23" marks, so label "hh"
is kept as hh:00 on the day, a naive `time`, not UTC and not claimed as an hour start
(Nicaraguan local time, UTC-6, is likely; a live check hints that labels may mark hour ends).
"""

import pandas as pd
import requests

DAY = "2026-10-15"
WIND_UNITS = ["AMY1", "AMY2", "EOL", "PBP", "ABR"]

resp = requests.get(
    "https://www.cndc.org.ni/MEMNDiarios/consultarPosdespachoEnergia",
    params={"fecha": pd.Timestamp(DAY).strftime("%d/%m/%Y")},
    timeout=60,
)
resp.raise_for_status()
rows = pd.DataFrame(resp.json()["posdespacho"])
rows = rows[rows["ggd"].isin(WIND_UNITS)]
if rows.empty:
    raise SystemExit(f"{DAY}: no wind unit rows (a demand-only day?)")

local = pd.to_datetime(DAY) + pd.to_timedelta(rows["fecha_hora"].astype(int), unit="h")
df = (
    rows.assign(
        time=local,  # zone and stamp end not stated
        unit_id=rows["ggd"],
        wind_mwh=pd.to_numeric(rows["valor"].str.replace(",", ".")),
    )
    .set_index("time")
    .sort_index()[["unit_id", "wind_mwh"]]
)
print(df)
print(f"{len(df)} unit-hours, {df['unit_id'].nunique()} units, {df['wind_mwh'].sum():.1f} MWh")
