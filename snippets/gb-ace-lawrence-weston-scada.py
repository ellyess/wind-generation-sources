# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pyarrow>=15", "requests>=2.32"]
# ///
"""Ten-minute output of ACE's 4.2 MW community turbine at Lawrence Weston, Bristol, for October
2026, from the ACE Wind Turbine Data on Zenodo (version 2026.10).

The 10-minute parquet (13 MB) stores one row per signal family, with the signals as a list of
name and value pairs; the turbine's own statistics are family wecstd. active_power_mean is the
10-minute mean in kW, the available-power columns show what the wind (and, after setpoints, the
grid) allowed, and energy_produced is a lifetime kWh counter. observed_at is UTC; whether it
opens or closes the 10 minutes is not stated, so stamps are kept as published. Traps handled:
the pairs are unpacked into columns; integer sentinels (65535, 6553.5, 4294967295 and so on)
are set to missing; a row ingested more than five minutes before its own stamp is dropped,
which removes the mis-stamped row after the autumn clock change (25 October 2026, 03:00 UTC),
leaving 02:00 to 03:00 UTC that day missing.
"""

import io

import pandas as pd
import requests

URL = "https://zenodo.org/records/23909980/files/ace-wind-2026-10m.parquet"  # version 2026.10
SIGNALS = {"active_power_mean": "power_kw",
           "available_power_by_wind_mean": "available_wind_kw",
           "available_power_after_external_setpoints_mean": "available_setpoint_kw",
           "energy_produced": "counter_kwh"}
SENTINELS = [65535, 65.535, 6553.5, 655.35, 2147483647, 4294967295]

resp = requests.get(URL, timeout=120)
resp.raise_for_status()
rows = pd.read_parquet(io.BytesIO(resp.content),
                       columns=["family", "observed_at", "ingested_at", "values"])
rows = rows[rows["family"] == "wecstd"]
rows = rows[rows["ingested_at"] > rows["observed_at"] - pd.Timedelta("5min")]

signals = pd.DataFrame([dict(pairs) for pairs in rows["values"]], index=rows["observed_at"])
df = (
    signals[list(SIGNALS)].rename(columns=SIGNALS)
    .mask(lambda d: d.isin(SENTINELS))
    .rename_axis("time_utc")
    .sort_index()
    .loc["2026-10"]
)
print(df)
mwh = df["power_kw"].sum() / 6 / 1000  # kW x 1/6 h -> kWh -> MWh
counter = (df["counter_kwh"].iloc[-1] - df["counter_kwh"].iloc[0]) / 1000
print(f"{len(df)} 10-minutes, {mwh:.0f} MWh from power, {counter:.0f} MWh on the counter")
