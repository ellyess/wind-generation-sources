# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Colombian hourly metered generation per wind plant for one day from XM's SiMEM.

Dataset 055A4D ("Generación real") gives kWh per plant and hour; wind plants are picked by
their "Eolica" tag in dataset E17D25 for the same day, because the plant master list omits them.
Traps handled: every plant-hour comes once per settlement version (TX1, TX2, TXR on this day),
so one version is kept per hour, the last in sort order (the publisher does not document how TXR
ranks against TX3 to TX6); plants are short codes, so names and capacity need another source.
FechaHora has no zone and no start/end statement, so it is kept as published, a naive `time`:
a day runs 00:00 to 23:00, which fits hour-start in Colombian time (UTC-5 all year), but XM does
not say so.
"""

import pandas as pd
import requests

DAY = "2026-10-01"
API = "https://www.simem.co/backend-files/api/PublicData"


def dataset(dataset_id: str) -> pd.DataFrame:
    params = {"startDate": DAY, "endDate": DAY, "datasetId": dataset_id}
    resp = requests.get(API, params=params, timeout=120)  # 055A4D is about 9 MB a day
    resp.raise_for_status()
    return pd.DataFrame(resp.json()["result"]["records"])


tags = dataset("E17D25")
wind_codes = set(tags.loc[tags["TipoGeneracion"] == "Eolica", "CodigoPlanta"])
rows = dataset("055A4D")
rows = rows[rows["CodigoPlanta"].isin(wind_codes)]
assert set(rows["UnidadMedida"]) == {"kWh"} and set(rows["CodigoDuracion"]) == {"PT1H"}
latest = rows.sort_values("Version").groupby(["CodigoPlanta", "FechaHora"]).tail(1)

df = (
    latest.assign(
        time=pd.to_datetime(latest["FechaHora"]),  # zone and stamp end not stated
        wind_mwh=latest["Valor"] / 1000,  # kWh -> MWh
    )
    .rename(columns={"CodigoPlanta": "unit_id", "Version": "version"})
    .set_index("time")
    .sort_index()[["unit_id", "version", "wind_mwh"]]
)
print(df)
print(f"{len(df)} plant-hours, {df['unit_id'].nunique()} wind plants, "
      f"{df['wind_mwh'].sum():.1f} MWh")
