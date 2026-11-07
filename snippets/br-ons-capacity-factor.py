# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pyarrow>=15", "requests>=2.32"]
# ///
"""Hourly output and capacity factor per Brazilian wind complex for one month, from ONS.

ONS's "Fator de Capacidade" file gives, per wind or solar complex and hour, verified generation
(val_geracaoverificada, MWmed: average MW over the hour), installed capacity (MW) and their
ratio. Traps handled:
- the file also holds solar complexes, so rows are filtered to "Eólica";
- the numbers are stored as decimals (text), so they are converted to floats;
- the time zone and which end of the hour din_instante marks are not documented. This snippet
  assumes the stamp is the start of the hour in Brasília clock time; since 2019 Brazil has had
  no daylight saving, so that is a fixed UTC-03:00. Before 2019, localise as America/Sao_Paulo.
Curtailment is inside the factor; remove it with ONS's constrained-off dataset.
"""

import io

import pandas as pd
import requests

MONTH = "2026_09"
URL = ("https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/fator_capacidade_2_di/"
       f"FATOR_CAPACIDADE-2_{MONTH}.parquet")

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
rows = pd.read_parquet(io.BytesIO(resp.content))
wind = rows[rows["nom_tipousina"] == "Eólica"]

df = (
    wind.assign(
        time_utc=wind["din_instante"].dt.tz_localize("-03:00").dt.tz_convert("UTC"),
        wind_mw=pd.to_numeric(wind["val_geracaoverificada"]),
        capacity_mw=pd.to_numeric(wind["val_capacidadeinstalada"]),
        capacity_factor=wind["val_fatorcapacidade"],
    )
    .rename(columns={"nom_usina_conjunto": "unit_id",
                     "val_latitudesecoletora": "lat", "val_longitudesecoletora": "lon"})
    .set_index("time_utc")
    .sort_index()[["unit_id", "lat", "lon", "wind_mw", "capacity_mw", "capacity_factor"]]
)
print(df)
fleet = df.groupby(level=0)[["wind_mw", "capacity_mw"]].sum()
print(f"{len(df)} complex-hours, {df['unit_id'].nunique()} complexes, "
      f"{df['wind_mw'].sum() / 1000:.0f} GWh, fleet mean "
      f"{fleet['wind_mw'].mean():.0f} MW of {fleet['capacity_mw'].mean():.0f} MW")
