# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Spanish daily wind energy for three days from Red Eléctrica's REData API.

estructura-generacion with time_trunc=day gives energy per day, stamped at the local midnight
that opens the day, with its offset (+01:00 or +02:00). Traps handled: the API gives no unit
("magnitude": null) and REE's web page labels the same numbers GWh, but they are MWh; the
documented hourly option fails, so daily is the finest; an error comes back as HTTP 400 or as an
HTML page, so the response is checked before parsing. The sample spans the March clock change.
"""

import pandas as pd
import requests

resp = requests.get(
    "https://apidatos.ree.es/en/datos/generacion/estructura-generacion",
    params={"start_date": "2024-03-30T00:00", "end_date": "2024-04-01T23:59", "time_trunc": "day"},
    timeout=60,
)
resp.raise_for_status()
assert resp.headers["Content-Type"].startswith("application/json"), resp.text[:200]
wind = next(s for s in resp.json()["included"] if s["type"] == "Wind")

values = pd.DataFrame(wind["attributes"]["values"])
df = (
    values.assign(time_utc=pd.to_datetime(values["datetime"], utc=True))  # local midnight, as UTC
    .set_index("time_utc")
    .sort_index()[["value", "percentage"]]
    .rename(columns={"value": "wind_mwh", "percentage": "share_of_generation"})
)
print(df)
print(f"{len(df)} days, {df['wind_mwh'].sum() / 1000:.1f} GWh")
