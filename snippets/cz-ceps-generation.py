# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "requests>=2.32"]
# ///
"""Czech wind output (WPP) for one day from ČEPS's CepsData SOAP web service, operation Generation.

Quarter-hour average MW for the whole Czech system, gross output, by plant type; WPP is wind.
The service runs in Prague local time and stamps each value with an explicit offset. ČEPS does
not say whether a stamp opens or closes its quarter hour; a request from 00:00 returns a first
stamp of 00:00, which fits the start, but that is not documented, so stamps are kept as given.
Traps handled:
the October change day repeats 02:00 with +02:00 and +01:00, so the offset is parsed rather than
the clock time (100 quarter hours); WPP is ČEPS's estimate, not metered output.
"""

import xml.etree.ElementTree as ET

import pandas as pd
import requests

BODY = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>
<Generation xmlns="https://www.ceps.cz/CepsData/">
<dateFrom>2025-10-26T00:00:00</dateFrom><dateTo>2025-10-26T23:59:59</dateTo>
<agregation>QH</agregation><function>AVG</function><version>RT</version><para1>all</para1>
</Generation></soap:Body></soap:Envelope>"""

resp = requests.post(
    "https://www.ceps.cz/_layouts/CepsData.asmx",
    data=BODY.encode(),
    headers={"Content-Type": "text/xml; charset=utf-8",
             "SOAPAction": '"https://www.ceps.cz/CepsData/Generation"'},
    timeout=60,
)
resp.raise_for_status()
ns = {"d": "https://www.ceps.cz/CepsData/StructuredData/1.0"}
root = ET.fromstring(resp.content)
names = {s.get("id"): s.get("name") for s in root.iterfind(".//d:serie", ns)}
assert names["value8"] == "WPP [MW]", names
items = [i.attrib for i in root.iterfind(".//d:item", ns)]

rows = pd.DataFrame(items)
df = (
    rows.assign(time_utc=pd.to_datetime(rows["date"], utc=True),  # offset-aware local stamps
                wind_mw=rows["value8"].astype(float))
    .set_index("time_utc")
    .sort_index()[["wind_mw"]]
)
print(df)
print(f"{len(df)} quarter hours, {df['wind_mw'].sum() * 0.25:.0f} MWh")  # MW x 0.25 h
