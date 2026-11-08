# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Annual gross wind generation in Lithuania, from the official statistics SDMX service.

Table S1R094 (structure M8020313) gives gross electricity production from renewables per year,
by installation type, in GWh. The snippet fetches the whole table as SDMX-ML (about 350 kB)
and keeps wind (code 06V). Traps handled:
- a series-key filter in the URL returns an empty message, so the full table is filtered here;
- years before wind existed are "NaN" with status "nebuvo" (category not applicable) and are
  dropped, not read as zero;
- the status column is kept, so the provisional latest year ("isankstiniai") is visible.
"""

import xml.etree.ElementTree as ET

import pandas as pd
import requests

URL = "https://osp-rs.stat.gov.lt/rest_xml/data/S1R094_M8020313"
G = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}"

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
records = []
for obs in ET.fromstring(resp.content).iter(f"{G}Obs"):
    rec = {v.get("id"): v.get("value") for v in obs.iter(f"{G}Value")}
    rec["value"] = obs.find(f"{G}ObsValue").get("value")
    records.append(rec)
rows = pd.DataFrame(records)

wind = rows[(rows["elektros_irenginiai"] == "06V") & (rows["MATVNT"] == "GWh")]
wind = wind.assign(wind_gwh=pd.to_numeric(wind["value"], errors="coerce")).dropna(
    subset=["wind_gwh"])
df = (wind.rename(columns={"LAIKOTARPIS": "period", "OBS_STATUS": "status"})
      .set_index("period").sort_index()[["wind_gwh", "status"]].fillna({"status": ""}))
print(df)
print(f"{len(df)} years, {df['wind_gwh'].sum():,.1f} GWh in all; {df.index[-1]}: "
      f"{df['wind_gwh'].iloc[-1]:,.1f} GWh")
