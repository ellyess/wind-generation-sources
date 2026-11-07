"""Annual wind generation totals read live from each source that allows it.

Each adapter fetches one calendar year from a catalogue entry's own data, with no key, and
returns the total in TWh. Where the adapter sums raw intervals it also reports how many it
found and the time step they imply, so the entry's stated resolution is checked too.

Only sources that need no key are read. Adding one means writing a function here and
registering it with @adapter("<entry id>").
"""

from __future__ import annotations

import calendar
import csv
import datetime as dt
import io
import json
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from wgs.checks.http import get, get_json

ISO3 = json.loads((Path(__file__).parents[1] / "data" / "iso3_to_iso2.json").read_text())
EUROSTAT_CODES = {"EL": "GR", "UK": "GB"}


@dataclass
class Total:
    source: str
    country: str
    twh: float
    intervals: int | None = None
    step_minutes: float | None = None
    via: str = ""
    note: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        d["twh"] = round(self.twh, 3)
        return {k: v for k, v in d.items() if v not in (None, "")}


ADAPTERS: dict[str, Callable[[int], list[Total]]] = {}


def adapter(entry_id: str):
    def register(fn: Callable[[int], list[Total]]):
        ADAPTERS[entry_id] = fn
        return fn
    return register


def _hours(year: int) -> int:
    return (366 if calendar.isleap(year) else 365) * 24


def _step(year: int, intervals: int, series: int = 1) -> float:
    return round(_hours(year) * 60 / (intervals / series), 2)


# References --------------------------------------------------------------------------------

@adapter("eu-eurostat-nrg-bal-peh")
def eurostat(year: int) -> list[Total]:
    url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_bal_peh"
           f"?format=JSON&lang=EN&time={year}&siec=RA300&nrg_bal=GEP&unit=GWH")
    data = get_json(url)
    index = data["dimension"]["geo"]["category"]["index"]
    out = []
    for code, pos in index.items():
        value = data["value"].get(str(pos))
        iso = EUROSTAT_CODES.get(code, code)
        if value is None or len(iso) != 2 or not iso.isalpha():
            continue
        out.append(Total("eu-eurostat-nrg-bal-peh", iso, value / 1000, via=url,
                         note="gross electricity production"))
    return out


@adapter("world-ember-monthly")
def ember(year: int) -> list[Total]:
    url = ("https://files.ember-energy.org/public-downloads/generation/outputs/"
           "release_generation_monthly_global.csv")
    months: dict[str, list[float]] = defaultdict(list)
    for row in csv.DictReader(io.StringIO(get(url, timeout=300).decode("utf-8"))):
        if (row["Area type"] == "Country or economy" and row["Electricity source"] == "Wind"
                and row["Date"].startswith(f"{year}-") and row["Generation (TWh)"]):
            iso = ISO3.get(row["ISO 3 code"])
            if iso:
                months[iso].append(float(row["Generation (TWh)"]))
    return [Total("world-ember-monthly", iso, sum(v), intervals=len(v), via=url,
                  note="sum of 12 monthly values")
            for iso, v in sorted(months.items()) if len(v) == 12]


@adapter("world-eia-international")
def eia_international(year: int) -> list[Total]:
    url = "https://www.eia.gov/opendata/bulk/INTL.zip"
    with zipfile.ZipFile(io.BytesIO(get(url, timeout=300))) as zf:
        text = zf.read(zf.namelist()[0]).decode("utf-8")
    out = []
    for line in text.splitlines():
        if '"INTL.37-12-' not in line or "-BKWH.A" not in line:
            continue
        series = json.loads(line)
        if "series_id" not in series:
            continue
        iso = ISO3.get(series["series_id"].split("-")[2])
        values = {str(y): v for y, v in series.get("data", [])}
        value = values.get(str(year))
        if iso and isinstance(value, (int, float)):
            out.append(Total("world-eia-international", iso, value, via=url,
                             note="net generation, billion kWh"))
    return out


@adapter("world-irena-irenastat")
def irena(year: int) -> list[Total]:
    url = ("https://pxweb.irena.org/api/v1/en/IRENASTAT/Power%20Capacity%20and%20Generation/"
           "Country_ELECSTAT_2026_H2_PX.px")
    query = {"query": [
        {"code": "Country/area", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Technology", "selection": {"filter": "item", "values": ["5", "21"]}},
        {"code": "Data Type", "selection": {"filter": "item", "values": ["0"]}},
        {"code": "Grid connection", "selection": {"filter": "item", "values": ["0"]}},
        {"code": "Year", "selection": {"filter": "item", "values": [str(year - 2000)]}},
    ], "response": {"format": "json"}}
    req = urllib.request.Request(url, data=json.dumps(query).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8-sig"))
    gwh: dict[str, float] = defaultdict(float)
    for row in data["data"]:
        iso = ISO3.get(row["key"][0])
        value = row["values"][0]
        if iso and value not in ("", "-", ".."):
            gwh[iso] += float(value)
    return [Total("world-irena-irenastat", iso, v / 1000, via=url,
                  note="onshore plus offshore, all grid connections")
            for iso, v in sorted(gwh.items()) if v > 0]


# National sources --------------------------------------------------------------------------

@adapter("es-ree-redata")
def ree(year: int) -> list[Total]:
    url = ("https://apidatos.ree.es/en/datos/generacion/estructura-generacion"
           f"?start_date={year}-01-01T00:00&end_date={year}-12-31T23:59&time_trunc=year")
    data = get_json(url)
    for item in data["included"]:
        if item["attributes"]["title"] == "Wind":
            mwh = sum(v["value"] for v in item["attributes"]["values"])
            return [Total("es-ree-redata", "ES", mwh / 1e6, via=url)]
    raise ValueError("no Wind series in the response")


@adapter("de-smard")
def smard(year: int) -> list[Total]:
    total, vias = 0.0, []
    for filt in (4067, 1225):  # onshore, offshore
        base = f"https://www.smard.de/app/chart_data/{filt}/DE/"
        stamps = get_json(base + "index_year.json")["timestamps"]
        start = [t for t in stamps
                 if (dt.datetime.fromtimestamp(t / 1000, dt.UTC) + dt.timedelta(hours=2)).year
                 == year]
        if not start:
            raise ValueError(f"no {year} file for filter {filt}")
        url = f"{base}{filt}_DE_year_{start[0]}.json"
        series = get_json(url)["series"]
        total += sum(v for _, v in series if v is not None)
        vias.append(url)
    return [Total("de-smard", "DE", total / 1e6, via=" ".join(vias),
                  note="onshore plus offshore yearly values")]


@adapter("fr-rte-eco2mix-national")
def eco2mix(year: int) -> list[Total]:
    for dataset in ("eco2mix-national-cons-def", "eco2mix-national-tr"):
        where = f'date_heure>="{year}-01-01" and date_heure<"{year + 1}-01-01"'
        url = ("https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
               f"{dataset}/records?" + urllib.parse.urlencode({
                   "select": "sum(eolien) as s, count(eolien) as n", "where": where,
                   "limit": 1}))
        res = get_json(url)["results"][0]
        if res["n"]:
            step = _step(year, res["n"])
            return [Total("fr-rte-eco2mix-national", "FR", res["s"] * step / 60 / 1e6,
                          intervals=res["n"], step_minutes=step, via=url,
                          note=f"dataset {dataset}; average MW times the observed step")]
    raise ValueError("no wind values for the year")


@adapter("gb-elexon-bmrs-fuel-type")
def fuelhh(year: int) -> list[Total]:
    periods: dict[tuple[str, int], float] = {}
    day = dt.date(year, 1, 1)
    while day.year == year:
        end = min(day + dt.timedelta(days=6), dt.date(year, 12, 31))
        url = ("https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH?"
               f"settlementDateFrom={day}&settlementDateTo={end}&fuelType=WIND&format=json")
        for row in get_json(url)["data"]:
            periods[(row["settlementDate"], row["settlementPeriod"])] = row["generation"]
        day = end + dt.timedelta(days=1)
    n = len(periods)
    return [Total("gb-elexon-bmrs-fuel-type", "GB", sum(periods.values()) * 0.5 / 1e6,
                  intervals=n, step_minutes=_step(year, n),
                  via="https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH",
                  note="FUELHH wind, average MW per settlement period")]


@adapter("dk-energinet-production-settlement")
def energinet(year: int) -> list[Total]:
    cols = ["OffshoreWindLt100MW_MWh", "OffshoreWindGe100MW_MWh", "OnshoreWindLt50kW_MWh",
            "OnshoreWindGe50kW_MWh"]
    # start and end are read as Danish local time, so ask for a wider window and cut on UTC.
    url = ("https://api.energidataservice.dk/dataset/ProductionConsumptionSettlement?"
           + urllib.parse.urlencode({
               "start": f"{year - 1}-12-31T00:00", "end": f"{year + 1}-01-02T00:00",
               "columns": ",".join(["HourUTC", "PriceArea", *cols]), "limit": 0}))
    rows = [r for r in get_json(url, timeout=300)["records"]
            if r["HourUTC"].startswith(str(year))]
    mwh = sum(r[c] or 0 for r in rows for c in cols)
    areas = len({r["PriceArea"] for r in rows})
    return [Total("dk-energinet-production-settlement", "DK", mwh / 1e6, intervals=len(rows),
                  step_minutes=_step(year, len(rows), areas), via=url,
                  note="four wind columns summed over both price areas")]


@adapter("be-elia-wind-production")
def elia(year: int) -> list[Total]:
    where = f'datetime>="{year}-01-01T00:00:00Z" and datetime<"{year + 1}-01-01T00:00:00Z"'
    url = ("https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods031/records?"
           + urllib.parse.urlencode({
               "select": "count(measured) as n, sum(measured) as s",
               "group_by": "region,gridconnectiontype,offshoreonshore", "where": where}))
    groups = get_json(url)["results"]
    n = groups[0]["n"]
    step = _step(year, n)
    total = sum(g["s"] for g in groups) * step / 60
    return [Total("be-elia-wind-production", "BE", total / 1e6, intervals=n,
                  step_minutes=step, via=url,
                  note=f"{len(groups)} region and grid rows summed")]


@adapter("nz-ea-emi-generation-md")
def emi(year: int) -> list[Total]:
    base = ("https://emidatasets.blob.core.windows.net/publicdata/Datasets/Wholesale/"
            "Generation/Generation_MD/")
    kwh = 0.0
    periods: dict[tuple[str, str], int] = defaultdict(int)
    for month in range(1, 13):
        text = get(f"{base}{year}{month:02d}_Generation_MD.csv", timeout=120).decode("utf-8")
        for row in csv.DictReader(io.StringIO(text)):
            if row["Fuel_Code"] != "Wind":
                continue
            values = [row[f"TP{i}"] for i in range(1, 51) if row.get(f"TP{i}")]
            kwh += sum(float(v) for v in values)
            periods[(row["Gen_Code"], row["POC_Code"])] += len(values)
    n = max(periods.values())  # the most complete connection point sets the step
    return [Total("nz-ea-emi-generation-md", "NZ", kwh / 1e9, intervals=n,
                  step_minutes=_step(year, n), via=base,
                  note="wind connection points summed, kWh per trading period")]


# Running -----------------------------------------------------------------------------------

STEP_OF = {"1s": 1 / 60, "1min": 1, "5min": 5, "10min": 10, "15min": 15, "30min": 30, "hourly": 60}


def run_totals(entries: list[dict], year: int, only: set[str] | None = None) -> dict:
    """Run every adapter whose entry exists, and record failures rather than stopping."""
    by_id = {e["id"]: e for e in entries}
    results, failures, step_checks = [], [], []
    for entry_id, fn in ADAPTERS.items():
        if entry_id not in by_id or (only and entry_id not in only):
            continue
        try:
            found = fn(year)
        except Exception as exc:
            failures.append({"source": entry_id, "error": str(exc)[:300]})
            continue
        results += found
        stated = STEP_OF.get(by_id[entry_id]["resolution"])
        for t in found:
            if t.step_minutes is not None and stated is not None:
                step_checks.append({
                    "source": entry_id, "stated_minutes": stated,
                    "observed_minutes": t.step_minutes,
                    "agrees": abs(t.step_minutes - stated) / stated < 0.02,
                })
    return {"year": year, "totals": [t.as_dict() for t in results], "failures": failures,
            "steps": step_checks}
