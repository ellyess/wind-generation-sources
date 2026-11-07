# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Hourly metered volumes for Alberta's wind farms for one month, from AESO's 2001-2025 release.

The CSV has one column per generating asset, with the hour's start in GMT and in local time.
Traps handled: the GMT column is used, so daylight saving does not matter; columns are bare
asset codes with no fuel type, so wind farms are picked from a fixed list of the codes AESO's
Current Supply Demand report shows under wind (read 2026-11-07; farms retired before then, such
as Cowley Ridge, are not in it); a blank cell means the asset was not yet registered and is
dropped, while zero is kept. Neither the file nor the page states the unit: the values are read
here as MWh in the hour, numerically average MW. The 2020-July 2025 file is about 52 MB and is
the smallest there is. April to July 2025 were not final, so an earlier month is used.
"""

import io

import pandas as pd
import requests

MONTH = "2024-01"
URL = ("https://www.aeso.ca/assets/Uploads/data-requests/"
       "Hourly_Metered_Volumes_and_Pool_Price_and_AIL_2020-Jul2025.csv")
WIND = """ARD1 BUL1 BUL2 BSR1 BTR1 BFL1 BFL2 BFL3 BFL4 BPW1 CR1 CRR2 CRR1 CRE3 CYP1 CYP2 TAB1
FRM1 FMG1 GDP1 NEP1 GRZ1 HAL2 HAL1 HHW1 HLD1 JNR1 JNR2 JNR3 KHW1 LAN1 AKE1 OWF1 PAW1 RTL1
RIV1 SHH1 GWW1 SWP1 IEW1 IEW2 SCR3 SCR2 WHE1 WHT1 WHT2 WIR1 WRW1 WIN1 SCR4""".split()

resp = requests.get(URL, timeout=300)
resp.raise_for_status()
wide = pd.read_csv(io.BytesIO(resp.content), low_memory=False)
time_utc = pd.to_datetime(wide["Date_Begin_GMT"], format="%Y-%m-%d %H:%M", utc=True)
wind = wide[[c for c in WIND if c in wide]].set_index(time_utc.rename("time_utc"))

df = (
    wind[wind.index.strftime("%Y-%m") == MONTH]
    .melt(var_name="unit_id", value_name="wind_mwh", ignore_index=False)
    .dropna(subset=["wind_mwh"])
    .sort_index()
)
print(df)
print(f"{len(df)} asset-hours, {df['unit_id'].nunique()} wind assets, "
      f"{df['wind_mwh'].sum() / 1e3:.0f} GWh (read as MWh per hour)")
