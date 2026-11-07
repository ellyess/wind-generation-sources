# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Island of Ireland metered wind output per unit for one day, from SEMO report BM-086.

Each unit's value is energy in MWh over a 30-minute settlement period, although the field is
called MeteredMW: it is summed as it is, never halved. StartTime marks the period start; the
files show it in UTC over the Irish calendar day (undocumented), so clock-change days have 46
or 50 periods. Traps handled:
- only about two months are online, so the latest trade date is listed through the reports API
  rather than a fixed file, and of its several versions the last published is kept;
- the meter file does not say which units are wind, so it is joined to the monthly Registered
  Capacity report (BM-003) on fuel type WIND;
- BM-003 tags solar farms as WIND, so units whose unit or participant name says solar or PV
  are dropped (TL1 is solar only by its participant, Tullabeg Solar Farm Limited). Unnamed WIND
  units are kept and counted; some of them may be solar too.
"""

import io

import pandas as pd
import requests

API = "https://reports.sem-o.com/api/v1/documents/static-reports"
DOCS = "https://reports.sem-o.com/documents/"


def latest(report: str) -> pd.DataFrame:
    """Download the most recent file of a SEMO static report as a DataFrame."""
    params = {"DPuG_ID": report, "page_size": 5, "sort_by": "Date", "order_by": "DESC"}
    items = pd.DataFrame(requests.get(API, params=params, timeout=60).json()["items"])
    name = items.sort_values(["Date", "PublishTime"]).iloc[-1]["ResourceName"]
    resp = requests.get(DOCS + name, timeout=120)
    resp.raise_for_status()
    tag = name.rsplit("_", 1)[0]  # PUB_DailyMeterDataD1 or PUB_MnlyRegisteredCapacity
    return pd.read_xml(io.BytesIO(resp.content), xpath=f".//{tag}", parser="etree")


units = latest("BM-003")
wind = units[units["FuelType"].eq("WIND")]
names = wind["UnitName"].fillna("") + " " + wind["ParticipantName"].fillna("")
solar = names.str.contains(r"solar|\bPV\b", case=False)
wind = wind[~solar]

meter = latest("BM-086")
meter = meter[meter["ResourceName"].isin(wind["ResourceName"])]
df = (
    meter.assign(time_utc=pd.to_datetime(meter["StartTime"]).dt.tz_localize("UTC"))
    .rename(columns={"ResourceName": "unit_id", "MeteredMW": "wind_mwh"})
    .set_index("time_utc")
    .sort_index()[["unit_id", "Jurisdiction", "wind_mwh"]]
)
print(df)
unnamed = wind["UnitName"].isna().sum()
print(f"{len(df)} unit half-hours, {df['unit_id'].nunique()} units ({solar.sum()} solar-named "
      f"dropped, {unnamed} unnamed kept), {df['wind_mwh'].sum() / 1000:.1f} GWh")  # MWh summed
