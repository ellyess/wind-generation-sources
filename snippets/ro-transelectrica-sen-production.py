# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Romania national wind power (MW) for one day from Transelectrica's SEN chart.

Uses the undocumented text resource the chart page itself calls: rows split by "|", fields by
";", in the order time, consumption, mean consumption, production, balance, coal, hydrocarbons,
hydro, nuclear, wind (Eolian), solar, biomass. Traps handled:
- values are instantaneous snapshots at drifting times about every 10 minutes, not averages
  or energy, so time is the snapshot instant (resample before joining to hourly data);
- some rows appear twice, so duplicates are dropped;
- a value containing ".00" is an estimate (shown with "*" on screen), kept as wind_estimated;
- stamps behave as Romanian local time, but Transelectrica does not say so, so they are kept
  as a naive `time`, not UTC. The sample is the autumn clock change, 25 October 2026, where the
  03:00 hour appears once, although local clocks ran through it twice.
Wind is zero on every row before mid-2010; treat those zeros as missing.
"""

import pandas as pd
import requests

DAY = pd.Timestamp("2026-10-25")
P = "_SENGrafic_WAR_SENGraficportlet_"
when = {"day": DAY.day, "month": DAY.month, "year": DAY.year}

resp = requests.get(
    "https://www.transelectrica.ro/widget/web/tel/sen-grafic",
    params={"p_p_id": "SENGrafic_WAR_SENGraficportlet", "p_p_lifecycle": 2,
            **{f"{P}start_{k}": v for k, v in when.items()}, f"{P}start_Hour": 0,
            f"{P}start_Minute": 0, **{f"{P}end_{k}": v for k, v in when.items()},
            f"{P}end_Hour": 23, f"{P}end_Minute": 59},
    timeout=120,
)
resp.raise_for_status()
fields = [r.split(";") for r in dict.fromkeys(resp.text.strip("|").split("|"))]  # dedupe rows
rows = pd.DataFrame({"local": [f[0] for f in fields], "wind": [f[9] for f in fields]})

local = pd.to_datetime(rows["local"], format="%d-%m-%Y %H:%M:%S")
df = (
    rows.assign(time=local,  # zone not stated
                wind_mw=pd.to_numeric(rows["wind"]),
                wind_estimated=rows["wind"].str.contains(".00", regex=False))
    .set_index("time")
    .sort_index()[["wind_mw", "wind_estimated"]]
)
print(df)
hourly = df["wind_mw"].resample("1h").mean()  # snapshots -> approximate hourly mean MW
print(f"{len(df)} snapshots, mean {df['wind_mw'].mean():,.0f} MW, "
      f"about {hourly.sum() / 1000:.1f} GWh from {hourly.count()} hourly means")
