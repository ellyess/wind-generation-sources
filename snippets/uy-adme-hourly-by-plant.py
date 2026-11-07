# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly energy per Uruguayan wind farm for March 2025 from ADME's operating-data panel.

The panel's form (variables_excel.php, a plain GET) returns a semicolon CSV of "Inyecciones
(MWh)" per plant and hour. Traps handled:
- the CSV can start with PHP warning lines, so lines before the plant-name header are skipped;
- "Inyecciones" and "Extracciones" are identical, so only the first is kept;
- a month before January 2019 silently returns January 2019, so the dates are checked;
- asking for several plants at once returned the right series only for the first column (Pampa
  and Valentines read near zero beside another plant, but about 29,900 and 16,300 MWh alone),
  so each plant is requested on its own.
ADME states neither the time zone nor the end of the period. A month runs from 01:00 on the
1st to 00:00 on the next 1st, which reads as hour-ending, so stamps are shifted back one hour
and read as Uruguay time (UTC-03:00, no daylight saving since 2015). Both are assumptions.
"""

import io

import pandas as pd
import requests

YEAR, MONTH = 2025, 3
PLANTS = {5: "Artilleros", 65: "Florida I", 119: "Pampa", 128: "Valentines"}  # panel ids

frames = []
for pid, name in PLANTS.items():
    resp = requests.get(
        "https://www.adme.com.uy/panelControl/variables_excel.php",
        params={"anod": YEAR, "mesd": f"{MONTH:02d}", "anoh": YEAR, "mesh": f"{MONTH:02d}",
                "periodo": 1, "tipo": 1, "central[]": pid},
        timeout=300,
    )
    resp.raise_for_status()
    lines = resp.text.splitlines()
    head = next(i for i, line in enumerate(lines) if line.startswith(";Inyecciones"))
    rows = pd.read_csv(io.StringIO("\n".join(lines[head + 1:])), sep=";", header=None,
                       usecols=[0, 1], names=["stamp", "wind_mwh"])
    end = pd.to_datetime(rows["stamp"], format="%d-%m-%Y %H:%M")
    start = (end - pd.Timedelta(hours=1)).dt.tz_localize("America/Montevideo")
    assert (start.dt.month == MONTH).all(), "ADME returned a different month"
    frames.append(rows.assign(time_utc=start.dt.tz_convert("UTC"), unit_id=name))

df = pd.concat(frames).set_index("time_utc").sort_index()[["unit_id", "wind_mwh"]]
print(df)
print(f"{len(df)} plant-hours, {df['wind_mwh'].sum():,.0f} MWh; "
      + ", ".join(f"{k} {v:,.0f}" for k, v in df.groupby("unit_id")["wind_mwh"].sum().items()))
