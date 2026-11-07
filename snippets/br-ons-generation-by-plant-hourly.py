# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pyarrow>=15", "requests>=2.32"]
# ///
"""Hourly verified generation per Brazilian wind plant or complex for one month, from ONS.

ONS's "Geração por Usina" file gives val_geracao in MWmed (average MW over the hour) for every
plant, complex and small-plant group in the interconnected system; wind rows have nom_tipousina
"EOLIELÉTRICA". Traps handled:
- small-plant groups ("Pequenas Usinas (Tipo III)", names "PQU ... EOL") are forecasts, not
  measurements, so they are dropped;
- the time zone and which end of the hour din_instante marks are not documented. This snippet
  assumes the stamp is the start of the hour in Brasília clock time; since 2019 Brazil has had
  no daylight saving, so that is a fixed UTC-03:00. Before 2019, localise as America/Sao_Paulo;
- the value is MW, not MWh, so energy is MW x 1 h.
"""

import io

import pandas as pd
import requests

MONTH = "2026_09"
URL = ("https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/geracao_usina_2_ho/"
       f"GERACAO_USINA-2_{MONTH}.parquet")

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
rows = pd.read_parquet(io.BytesIO(resp.content))

wind = rows[(rows["nom_tipousina"] == "EOLIELÉTRICA")
            & ~rows["cod_modalidadeoperacao"].str.contains("Tipo III", case=False)]
df = (
    wind.assign(
        time_utc=wind["din_instante"].dt.tz_localize("-03:00").dt.tz_convert("UTC"),
        wind_mw=pd.to_numeric(wind["val_geracao"]),
    )
    .rename(columns={"nom_usina": "unit_id", "id_estado": "state"})
    .set_index("time_utc")
    .sort_index()[["unit_id", "state", "cod_modalidadeoperacao", "wind_mw"]]
)
print(df)
print(f"{len(df)} plant-hours, {df['unit_id'].nunique()} plants, "
      f"{df['wind_mw'].sum() / 1000:.0f} GWh")  # MW x 1 h
