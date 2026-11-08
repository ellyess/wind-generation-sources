"""Prototype: match market unit codes to OpenStreetMap wind farms.

Several catalogue sources publish output per unit (AEMO dispatch units, Elexon balancing
mechanism units, IESO generators) with no location. OpenStreetMap maps most wind farms with a
name, a capacity and a position. This script proposes a link from each unit to an OSM wind farm,
scores it, and writes one CSV per market for a person to review. In Great Britain, Wikidata's
links from balancing mechanism unit codes to power stations (property P11610, CC0) take
precedence over the name matches (see `apply_wikidata`).

Nothing here is a verified link until someone reviews it. The output is derived from
OpenStreetMap, so it is under the Open Database License (ODbL), not CC BY like the catalogue.

    uv run --with openpyxl python crosswalk/build.py            # fetch what is missing, then match
    uv run --with openpyxl python crosswalk/build.py --refresh  # fetch everything again
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from math import log
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
OUT = HERE / "output"
UA = "wind-generation-sources-crosswalk/0.1 (+https://github.com/ellyess/wind-generation-sources)"

SOURCES = {
    "elexon_bmunits.json": "https://data.elexon.co.uk/bmrs/api/v1/reference/bmunits/all",
    "ieso_cap.xml": "https://reports-public.ieso.ca/public/GenOutputCapability/PUB_GenOutputCapability.xml",
    "aemo_reg.xlsx": "https://www.aemo.com.au/-/media/Files/Electricity/NEM/Participant_Information/NEM-Registration-and-Exemption-List.xlsx",
    # OSUKED Power Station Dictionary (MIT): names the station behind each Elexon unit and gives
    # its Renewable Energy Planning Database (REPD) id. Pinned to the last data commit.
    "psd_ids.csv": "https://raw.githubusercontent.com/OSUKED/Power-Station-Dictionary/839304f04a9a37e317e69009ea2f9a05e4883362/data/dictionary/ids.csv",
    # Renewable Energy Planning Database, July 2026 extract (DESNZ, Open Government Licence v3.0).
    # Listed at gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract
    "repd.csv": "https://assets.publishing.service.gov.uk/media/6a6cbdc00c36759b5ccaa305/REPD_Publication_Q2_2026.csv",
}
REPD_STATUSES = {"Operational", "Under Construction", "Awaiting Construction"}
OSM_AREAS = {"gb": ("ISO3166-1", "GB"), "au": ("ISO3166-1", "AU"), "on": ("ISO3166-2", "CA-ON")}
OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"]

# Words that say "this is a wind farm" rather than which one.
STOP = {
    "wind", "farm", "farms", "windfarm", "windfarms", "wf", "energy", "park", "windpark",
    "project", "owf", "power", "station", "renewable", "renewables", "pty", "ltd", "limited", "plc",
    "llp", "lp", "inc",
    "the", "of", "and", "generation", "generating", "facility", "centre", "center", "company", "co",
    "holdings", "operations", "offshore", "onshore", "scheme", "development", "developments",
    "trading", "uk", "gb", "trust", "partnership", "corporation", "corp", "unit",
}
# Place words shared by many farms: matching on these alone proves nothing.
GENERIC = {
    "creek", "hill", "hills", "range", "ranges", "mountain", "mount", "mt", "ridge", "lake",
    "lakes",
    "river", "point", "bay", "island", "north", "south", "east", "west", "port", "valley", "plains",
    "plain", "moor", "moss", "fell", "forest", "glen", "head", "bank", "banks", "field", "fields",
    "green", "new", "upper", "lower", "high", "great", "little", "cross", "burn", "loch", "beck",
    "law", "rig", "knowe", "muir", "1", "2", "3", "4", "5", "a", "b", "extension", "stage",
}
NUMBERS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "i": "1", "ii": "2",
           "iii": "3", "iv": "4", "a": "a", "b": "b"}
# Lead parties that are traders or large utilities: their name says nothing about the site.
GENERIC_PARTIES = re.compile(
    r"\b(sse|rwe|scottishpower|iberdrola|edf|e\.?on|centrica|statkraft|orsted|ørsted|vattenfall|"
    r"npower|drax|uniper|engie|good energy|octopus|bryt|smartest|limejump|flexitricity|"
    r"axpo|danske|shell|bp|equinor|total|nextera|ecotricity|infinis|brookfield|enel|"
    r"zenobe|habitat|statkraft|power ni|ovo|bord|esb|electricity supply|smartestenergy|mobius|"
    r"erova|eneco|sp renewables|edgware|markets|trading|trade|customers|supply)\b", re.I)


def fetch(name: str, url: str | list[str], refresh: bool, data: bytes | None = None) -> Path:
    path = CACHE / name
    if path.exists() and path.stat().st_size and not refresh:
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    errors = []
    for u in [url] if isinstance(url, str) else url:
        req = urllib.request.Request(u, data=data, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=300) as res:
                body = res.read()
        except OSError as exc:  # busy Overpass servers answer 429 or 504: try the next
            errors.append(f"{u}: {exc}")
            continue
        path.write_bytes(body)
        return path
    raise OSError("; ".join(errors))


# Offshore farms beyond territorial waters fall outside a country's area: add them by box.
OFFSHORE_BOX = {"gb": "(49.0,-8.5,61.5,3.5)"}


def fetch_osm(area: str, refresh: bool) -> list[dict]:
    key, value = OSM_AREAS[area]
    sel = 'nwr["power"="plant"]["plant:source"="wind"]'
    extra = ""
    if area in OFFSHORE_BOX:
        box = OFFSHORE_BOX[area]
        extra = (f'{sel}["offshore"="yes"]{box};{sel}[name~"[Oo]ffshore"]{box};'
                 # Farms tagged another way: mixed sources ("wind;solar"), or still being built.
                 f'nwr["power"="plant"]["plant:source"~"wind"]["plant:source"!="wind"]{box};'
                 f'nwr["construction:power"="plant"][name~"[Ww]ind"]{box};')
    query = (f'[out:json][timeout:180];area["{key}"="{value}"][admin_level]->.a;'
             f'({sel}(area.a);{extra});out center tags;')
    data = urllib.parse.urlencode({"data": query}).encode()
    path = fetch(f"osm_plants_{area}.json", OVERPASS, refresh, data)
    return json.loads(path.read_text())["elements"]


# ---------- names and capacities ----------

def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def tokens(text: str) -> list[str]:
    out = []
    for t in fold(text).split():
        t = NUMBERS.get(t, t)
        if t not in STOP:
            out.append(t)
    return out


def join_compounds(ta: list[str], tb: list[str]) -> list[str]:
    """Join adjacent words in tb that one word in ta spells as one: "Dogger Bank", "Doggerbank"."""
    out, i = [], 0
    while i < len(tb):
        if i + 1 < len(tb) and tb[i] + tb[i + 1] in ta:
            out.append(tb[i] + tb[i + 1])
            i += 2
        else:
            out.append(tb[i])
            i += 1
    return out


def name_score(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    ta, tb = join_compounds(tb, ta), join_compounds(ta, tb)
    sa, sb = set(ta), set(tb)
    ratio_only = difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    if not (sa & sb) - GENERIC:
        # No distinctive word in common: only a near-identical spelling counts.
        return ratio_only if ratio_only >= 0.85 else min(ratio_only, 0.5)
    # Containment: "Macarthur" against "Macarthur Wind Farm Stage 1" is a strong match.
    contain = len(sa & sb) / min(len(sa), len(sb))
    ratio = difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    # A digit present on one side and different on the other (stage 1 vs stage 2) is a penalty.
    da, db = {t for t in sa if t.isdigit()}, {t for t in sb if t.isdigit()}
    penalty = 0.15 if da and db and not (da & db) else 0.0
    return max(0.0, max(contain * 0.95, ratio) - penalty)


def parse_mw(value: str | None) -> float | None:
    if not value:
        return None
    m = re.match(r"\s*([\d.,]+)\s*(gw|mw|kw|w)?\b", value.lower())
    if not m:
        return None
    try:
        num = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = m.group(2) or "mw"
    return num * {"gw": 1000, "mw": 1, "kw": 0.001, "w": 1e-6}[unit]


@dataclass
class Plant:
    osm_type: str
    osm_id: int
    names: list[str]
    capacity_mw: float | None
    lat: float
    lon: float
    tags: dict = field(repr=False)

    @property
    def name(self) -> str:
        return self.names[0] if self.names else ""


def load_plants(elements: list[dict]) -> list[Plant]:
    plants = []
    for e in elements:
        t = e.get("tags", {})
        keys = ("name", "name:en", "official_name", "alt_name", "old_name", "short_name")
        names = [t[k] for k in keys if t.get(k)]
        names += [n for k in ("alt_name",) for n in t.get(k, "").split(";")[1:] if n]
        sources = ";".join(t.get(k, "") for k in ("plant:source", "construction:plant:source"))
        if (sources.strip(";") and "wind" not in sources) or re.search(
                r"\b(battery|bess|solar farm)\b", t.get("name", ""), re.I):
            continue  # a battery or solar site whose name happens to mention wind
        lat = e.get("lat", e.get("center", {}).get("lat"))
        lon = e.get("lon", e.get("center", {}).get("lon"))
        if lat is None:
            continue
        plants.append(Plant(e["type"], e["id"], names, parse_mw(t.get("plant:output:electricity")),
                            lat, lon, t))
    return plants


# ---------- the Renewable Energy Planning Database (GB) ----------

def bng_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """British National Grid (OSGB36, EPSG:27700) to WGS84 latitude and longitude.

    Ordnance Survey's transverse Mercator inverse, then a seven-parameter Helmert shift.
    Good to a few metres, far finer than a wind farm.
    """
    from math import atan2, cos, radians, sin, sqrt, tan

    a, b, f0 = 6377563.396, 6356256.909, 0.9996012717  # Airy 1830, national grid scale
    lat0, lon0, n0, e0 = radians(49), radians(-2), -100000.0, 400000.0
    e2 = 1 - (b * b) / (a * a)
    n = (a - b) / (a + b)

    def meridional(phi: float) -> float:
        d, s_ = phi - lat0, phi + lat0
        return b * f0 * ((1 + n + 1.25 * n**2 + 1.25 * n**3) * d
                         - (3 * n + 3 * n**2 + 2.625 * n**3) * sin(d) * cos(s_)
                         + (1.875 * n**2 + 1.875 * n**3) * sin(2 * d) * cos(2 * s_)
                         - (35 / 24) * n**3 * sin(3 * d) * cos(3 * s_))

    phi = (northing - n0) / (a * f0) + lat0
    while abs(northing - n0 - meridional(phi)) >= 1e-5:
        phi += (northing - n0 - meridional(phi)) / (a * f0)
    nu = a * f0 / sqrt(1 - e2 * sin(phi) ** 2)
    rho = a * f0 * (1 - e2) / (1 - e2 * sin(phi) ** 2) ** 1.5
    eta2 = nu / rho - 1
    t, sec = tan(phi), 1 / cos(phi)
    de = easting - e0
    lat = (phi - t / (2 * rho * nu) * de**2
           + t / (24 * rho * nu**3) * (5 + 3 * t**2 + eta2 - 9 * t**2 * eta2) * de**4
           - t / (720 * rho * nu**5) * (61 + 90 * t**2 + 45 * t**4) * de**6)
    lon = (lon0 + sec / nu * de
           - sec / (6 * nu**3) * (nu / rho + 2 * t**2) * de**3
           + sec / (120 * nu**5) * (5 + 28 * t**2 + 24 * t**4) * de**5
           - sec / (5040 * nu**7) * (61 + 662 * t**2 + 1320 * t**4 + 720 * t**6) * de**7)

    # OSGB36 to WGS84: to Cartesian on Airy, Helmert shift, back to geodetic on WGS84.
    nu_a = a / sqrt(1 - e2 * sin(lat) ** 2)
    x = nu_a * cos(lat) * cos(lon)
    y = nu_a * cos(lat) * sin(lon)
    z = nu_a * (1 - e2) * sin(lat)
    # Ordnance Survey's WGS84-to-OSGB36 parameters, negated for the reverse direction.
    tx, ty, tz, scale = 446.448, -125.157, 542.060, -20.4894e-6
    rx, ry, rz = (radians(v / 3600) for v in (0.1502, 0.2470, 0.8421))
    x2 = tx + (1 + scale) * x - rz * y + ry * z
    y2 = ty + rz * x + (1 + scale) * y - rx * z
    z2 = tz - ry * x + rx * y + (1 + scale) * z
    aw, bw = 6378137.0, 6356752.3142
    e2w = 1 - (bw * bw) / (aw * aw)
    p_ = sqrt(x2 * x2 + y2 * y2)
    lat_w = atan2(z2, p_ * (1 - e2w))
    for _ in range(10):
        nu_w = aw / sqrt(1 - e2w * sin(lat_w) ** 2)
        lat_w = atan2(z2 + e2w * nu_w * sin(lat_w), p_)
    from math import degrees
    return degrees(lat_w), degrees(atan2(y2, x2))


def load_repd(path: Path) -> list[Plant]:
    """Wind sites from the REPD that are built, being built or about to be, as Plant records.

    Both the current and the old REPD reference go in the "repd:id" tag, so a unit's id from
    the Power Station Dictionary joins whichever one it carries.
    """
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig") if raw[:3] == b"\xef\xbb\xbf" else raw.decode("cp1252")
    plants = []
    for r in csv.DictReader(text.splitlines()):
        if not r.get("Technology Type", "").startswith("Wind"):
            continue
        if r.get("Development Status (short)", "").strip() not in REPD_STATUSES:
            continue
        try:
            lat, lon = bng_to_wgs84(float(r["X-coordinate"]), float(r["Y-coordinate"]))
        except (KeyError, ValueError):
            continue
        ids = ";".join(v for v in (r.get("Ref ID", "").strip(), r.get("Old Ref ID", "").strip())
                       if v)
        tags = {"repd:id": ids, "status": r["Development Status (short)"].strip(),
                "technology": r["Technology Type"]}
        plants.append(Plant("repd", ids.split(";")[0], [r.get("Site Name", "").strip()],
                            parse_mw(r.get("Installed Capacity (MWelec)")), lat, lon, tags))
    return plants


# ---------- units ----------

@dataclass
class Unit:
    market: str
    unit_id: str
    names: list[str]
    capacity_mw: float | None
    capacity_kind: str
    extra: dict


def load_aemo(path: Path) -> list[Unit]:
    from openpyxl import load_workbook

    ws = load_workbook(path, read_only=True, data_only=True)["PU and Scheduled Loads"]
    rows = ws.iter_rows(values_only=True)
    head = [str(h).strip() if h else "" for h in next(rows)]
    units = []
    for r in rows:
        rec = dict(zip(head, r, strict=False))
        duid = str(rec.get("DUID") or "").strip()
        if "wind" not in str(rec.get("Fuel Source - Primary", "")).lower() or duid in ("", "-"):
            continue
        cap = rec.get("Reg Cap generation (MW)")
        units.append(Unit("aemo-nem", str(rec["DUID"]), [str(rec.get("Station Name") or "")],
                          float(cap) if cap not in (None, "") else None, "registered",
                          {"region": rec.get("Region"), "participant": rec.get("Participant")}))
    return units


def bmu_stem(code: str) -> str:
    """WHILW-1 -> whil. Elexon wind units often end their stem in W (wind) or O (offshore)."""
    stem = code.split("-")[0].lower()
    return re.sub(r"[wo]$", "", stem) if len(stem) > 4 else stem


def load_psd(path: Path) -> dict[str, dict]:
    """Power Station Dictionary rows keyed by every Elexon and National Grid unit code."""
    by_code = {}
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            for col in ("sett_bmu_id", "ngc_bmu_id"):
                for code in (r.get(col) or "").split(","):
                    if code.strip():
                        by_code[code.strip()] = r
    return by_code


def load_elexon(path: Path, psd: dict[str, dict]) -> list[Unit]:
    units = []
    for b in json.loads(path.read_text()):
        if (b.get("fuelType") or "").upper() != "WIND":
            continue
        party = b.get("leadPartyName") or ""
        names = [] if GENERIC_PARTIES.search(party) else [party]
        ng = b.get("nationalGridBmUnit") or ""
        code = b.get("elexonBmUnit") or ng
        entry = psd.get(code) or psd.get(ng) or {}
        if entry.get("name"):
            names.insert(0, entry["name"])
        repd = {v.strip() for k in ("new_repd_id", "old_repd_id")
                for v in (entry.get(k) or "").split(",") if v.strip()}
        cap = b.get("generationCapacity")
        units.append(Unit("elexon-bm", code, names, float(cap) if cap else None, "registered",
                          {"ng_code": ng, "lead_party": party, "eic": b.get("eic") or "",
                           "repd": repd, "psd_name": entry.get("name", ""),
                           "aggregate": b.get("bmUnitType") == "S"}))
    return units


def load_ieso(path: Path) -> list[Unit]:
    ns = {"i": "http://www.theIMO.com/schema"}
    units = []
    for g in ET.parse(path).getroot().findall(".//i:Generator", ns):
        if g.findtext("i:FuelType", namespaces=ns) != "WIND":
            continue
        caps = [float(c.findtext("i:EnergyMW", namespaces=ns) or 0)
                for c in g.findall(".//i:Capability", ns)]
        name = g.findtext("i:GeneratorName", namespaces=ns)
        # Report codes such as MCLEANSMTNWF-LT.AG_T1 or GOSFIELDWGS: strip the plumbing.
        clean = re.sub(r"-LT\.AG_\w+$|-T\d+$", "", name)
        clean = re.sub(r"(WF|WGS|WIND|FARM|NRWF)$", "", clean.replace(" NRWF", "")).strip()
        clean = clean.replace("MTN", " MOUNTAIN ")
        units.append(Unit("ieso", name, [clean], max(caps) if caps else None,
                          "floor (highest hourly capability in the report)", {}))
    return units


# ---------- matching ----------

def candidates(unit: Unit, plants: list[Plant]) -> list[tuple[float, str, Plant]]:
    scored = []
    repd = unit.extra.get("repd") or set()
    for p in plants:
        best, how = 0.0, ""
        if repd & {v.strip() for v in p.tags.get("repd:id", "").split(";")}:
            scored.append((1.0, "repd-id", p))
            continue
        for un in unit.names:
            for pn in p.names:
                s = name_score(un, pn)
                if s > best:
                    best, how = s, "name"
        stem = bmu_stem(unit.extra.get("ng_code", "")) if unit.market == "elexon-bm" else ""
        if len(stem) >= 4:
            for pn in p.names:
                first = "".join(tokens(pn))
                if first.startswith(stem):
                    s = 0.7 if len(stem) >= 5 else 0.6
                    if s > best:
                        best, how = s, "code-prefix"
        if best > 0.45:
            scored.append((best, how, p))
    def cap_gap(p: Plant) -> float:
        if not (unit.capacity_mw and p.capacity_mw):
            return 1.0
        return abs(1 - unit.capacity_mw / p.capacity_mw)

    # Near-equal names (stages, duplicates): prefer the farm whose capacity fits the unit.
    scored.sort(key=lambda x: (x[1] != "repd-id", -round(x[0] / 0.05), cap_gap(x[2])))
    return scored


def same_farm(a: Plant, b: Plant) -> bool:
    """The same farm mapped twice (an area and a relation, say): same name, within 5 km."""
    close = abs(a.lat - b.lat) < 0.045 and abs(a.lon - b.lon) < 0.07
    return close and tokens(a.name) == tokens(b.name)


def classify(score: float, how: str, ratio: float | None, margin: float, floor: bool) -> str:
    # A floor (IESO) can only rule a farm out by exceeding it.
    cap_ok = ratio is None or (ratio <= 1.2 if floor else 0.35 <= ratio <= 1.6)
    # A shared planning-database id is a direct key, not a guess.
    if how == "repd-id":
        return "proposed" if cap_ok else "review"
    if how == "name" and score >= 0.85 and cap_ok and margin >= 0.1:
        return "proposed"
    # A unit code that spells the farm's name, and capacities that agree within 10%,
    # are two independent pieces of evidence.
    if how == "code-prefix" and ratio and not floor and 0.9 <= ratio <= 1.1 and margin >= 0.1:
        return "proposed"
    if score >= 0.6:
        return "review"
    return "unmatched"


FIELDS = ["market", "unit_id", "unit_name", "unit_capacity_mw", "unit_capacity_kind", "status",
          "method", "score", "location_source", "farm_name", "farm_state", "farm_capacity_mw",
          "farm_capacity_ratio", "lat", "lon", "osm_url", "repd_id", "wikidata", "runner_up",
          "notes"]
RANK = {"proposed": 3, "review": 2, "unmatched": 1}


def farm_state(p: Plant) -> str:
    if p.osm_type == "repd":
        return p.tags["status"].lower()
    return "under construction" if p.tags.get("construction:power") == "plant" else "operating"


def match_market(units: list[Unit], plants: list[Plant]) -> list[dict]:
    rows = []
    for u in units:
        cands = candidates(u, plants)
        row = {"market": u.market, "unit_id": u.unit_id,
               "unit_name": "; ".join(n for n in u.names if n),
               "unit_capacity_mw": u.capacity_mw, "unit_capacity_kind": u.capacity_kind,
               "status": "unmatched", "notes": ""}
        if u.market == "elexon-bm":
            row["unit_name"] = row["unit_name"] or f"(lead party: {u.extra['lead_party']})"
            if u.extra.get("aggregate"):
                # Supplier units sum many small embedded sites: there is no single farm.
                row.update(status="aggregate", notes="supplier unit: many sites, no single farm")
                rows.append(row)
                continue
        if cands:
            score, how, p = cands[0]
            others = [c for c in cands[1:] if not same_farm(c[2], p)]
            runner = others[0] if others else None
            from_repd = p.osm_type == "repd"
            row.update({
                "method": how, "score": round(score, 2), "_plant": p,
                "location_source": "repd" if from_repd else "osm",
                "_tech": p.tags.get("technology", ""),
                "osm_url": "" if from_repd else f"https://www.openstreetmap.org/{p.osm_type}/{p.osm_id}",
                "farm_name": p.name, "farm_state": farm_state(p), "farm_capacity_mw": p.capacity_mw,
                "lat": round(p.lat, 5), "lon": round(p.lon, 5),
                "repd_id": p.tags.get("repd:id", ""), "wikidata": p.tags.get("wikidata", ""),
                "runner_up": f"{runner[2].name} ({runner[0]:.2f})" if runner else "",
                "_margin": score - (runner[0] if runner else 0),
            })
        rows.append(row)

    # Several units often share one farm (stages, or one unit per connection). Compare the sum
    # of the units' capacity with the farm's, not each unit alone.
    by_plant = defaultdict(list)
    for r in rows:
        if "_plant" in r and r["score"] >= 0.6:
            by_plant[id(r["_plant"])].append(r)
    for group in by_plant.values():
        p = group[0]["_plant"]
        caps = [r["unit_capacity_mw"] for r in group if r["unit_capacity_mw"]]
        ratio = sum(caps) / p.capacity_mw if caps and p.capacity_mw else None
        for r in group:
            r["farm_capacity_ratio"] = round(ratio, 2) if ratio else ""
            floor = r["unit_capacity_kind"].startswith("floor")
            r["status"] = classify(r["score"], r["method"], ratio, r["_margin"], floor)
            if len(group) > 1:
                r["notes"] = f"{len(group)} units point at this farm"
            if ratio and not (ratio <= 1.2 if floor else 0.35 <= ratio <= 1.6):
                r["notes"] = (r["notes"] + "; " if r["notes"] else "") + "capacity disagrees"
    for r in rows:
        r.pop("_plant", None)
        r.pop("_margin", None)
    return rows


def capacity_gap(row: dict) -> float:
    """How far a row's summed unit capacity is from its farm's, as a log ratio."""
    ratio = row.get("farm_capacity_ratio")
    return abs(log(ratio)) if isinstance(ratio, (int, float)) and ratio > 0 else float("inf")


def add_repd_fallback(units: list[Unit], rows: list[dict], repd: list[Plant]) -> list[dict]:
    """Second pass for GB units OSM could not place: the planning database's own sites.

    A unit whose Power Station Dictionary REPD id matches a site joins directly; the rest are
    matched by name and capacity under the same rules as OSM. A REPD row replaces the OSM row
    only when its status is strictly better, so OSM links are kept wherever they exist.
    """
    todo = [u for u, r in zip(units, rows, strict=True)
            if r["status"] in ("review", "unmatched")]
    second = {r["unit_id"]: r for r in match_market(todo, repd)}
    # Offshore sites in REPD often share one zone-level point (East Anglia 1, 3 and 4 do).
    shared = Counter((round(p.lat, 4), round(p.lon, 4)) for p in repd)
    out = []
    for r in rows:
        alt = second.get(r["unit_id"])
        if alt and (RANK.get(alt["status"], 0) > RANK.get(r["status"], 0)
                    or (alt["status"] == r["status"] == "review"
                        and capacity_gap(alt) < capacity_gap(r))):
            alt = dict(alt)
            notes = [alt["notes"]]
            if r["status"] == "review":
                notes.append(f"OSM candidate was {r['farm_name']} (review)")
            n = shared[(round(alt["lat"], 4), round(alt["lon"], 4))]
            if n > 1:
                notes.append(f"REPD gives this point to {n} sites: zone-level location")
            elif "offshore" in alt.get("_tech", "").lower():
                notes.append("REPD offshore point: can be tens of km from the turbines")
            alt["notes"] = "; ".join(filter(None, notes))
            r = alt
        out.append(r)
    return out


def check_repd_names(units: list[Unit], rows: list[dict], repd: list[Plant]) -> None:
    """Demote an ID join when REPD's own name for that ID shares nothing with the unit's names.

    The Power Station Dictionary has a few wrong IDs: among East Anglia One's it lists Hornsea 1's,
    so the join lands on the wrong farm with full confidence.
    """
    by_id = {i: p for p in repd for i in p.tags["repd:id"].split(";")}
    for u, r in zip(units, rows, strict=True):
        if r.get("method") != "repd-id":
            continue
        # The ID the join used: the dictionary sometimes lists several, one of them wrong.
        used = set(re.split(r"[;,\s]+", r["repd_id"])) & set(u.extra.get("repd") or ())
        sites = {by_id[i].name for i in used if i in by_id}
        mine = {t for n in u.names for t in tokens(n)} - GENERIC
        theirs = {t for s in sites for t in tokens(s)} - GENERIC
        if sites and not mine & theirs:
            r["status"] = "review" if r["status"] == "proposed" else r["status"]
            r["notes"] = "; ".join(filter(None, [r["notes"],
                f"REPD names this ID {' / '.join(sorted(sites))}, not the unit's station"]))


# ---------- Wikidata's links from balancing mechanism units to farms (GB) ----------

# Wikidata property P11610, "National Grid Balancing Mechanism unit ID": the unit's National Grid
# code (WHILW-1), on the item for the power station. Its formatter points at Elexon's BM unit list.
# Wikidata is CC0 and community-edited, so a link is evidence, not a verified fact.
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
# P625 coordinates, P2109 nameplate capacity (normalised to watts), P402 OSM relation,
# P9891 REPD id, P31 instance of.
WIKIDATA_QUERY = """
SELECT ?item ?itemLabel
  (GROUP_CONCAT(DISTINCT ?bmu; separator=";") AS ?bmus)
  (GROUP_CONCAT(DISTINCT STR(?coord); separator=";") AS ?coords)
  (GROUP_CONCAT(DISTINCT STR(?watts); separator=";") AS ?capacity_w)
  (GROUP_CONCAT(DISTINCT ?osm; separator=";") AS ?osm_relations)
  (GROUP_CONCAT(DISTINCT ?repd; separator=";") AS ?repd_ids)
  (GROUP_CONCAT(DISTINCT ?typeLabel; separator=";") AS ?types)
WHERE {
  ?item wdt:P11610 ?bmu .
  OPTIONAL { ?item wdt:P625 ?coord . }
  OPTIONAL { ?item p:P2109/psn:P2109/wikibase:quantityAmount ?watts . }
  OPTIONAL { ?item wdt:P402 ?osm . }
  OPTIONAL { ?item wdt:P9891 ?repd . }
  OPTIONAL { ?item wdt:P31 ?type . ?type rdfs:label ?typeLabel . FILTER(LANG(?typeLabel) = "en") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
GROUP BY ?item ?itemLabel
"""
WIKIDATA_UA = f"{UA} unit-to-farm crosswalk, Python urllib"
# Two points for the same farm closer than this agree; farther apart, the old one has "moved".
AGREE_KM = 5.0


@dataclass
class WikidataItem:
    qid: str
    label: str
    bmus: set[str]
    points: list[tuple[float, float]]  # (lat, lon)
    capacities_mw: list[float]
    osm_relations: set[int]
    repd_ids: set[str]
    types: set[str]

    @property
    def is_wind(self) -> bool:
        return any("wind" in t.lower() for t in self.types)


def fetch_wikidata(refresh: bool) -> Path:
    """The SPARQL answer, cached as `.cache/wikidata/bmu_items.json`. Keyless."""
    path = CACHE / "wikidata" / "bmu_items.json"
    if path.exists() and path.stat().st_size and not refresh:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    url = WIKIDATA_SPARQL + "?" + urllib.parse.urlencode({"query": WIKIDATA_QUERY,
                                                          "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_UA,
                                               "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=300) as res:
        path.write_bytes(res.read())
    return path


def load_wikidata(path: Path) -> dict[str, WikidataItem]:
    """Wikidata items keyed by every BM unit code they carry."""
    by_code = {}
    for b in json.loads(path.read_text())["results"]["bindings"]:
        def get(key: str, b: dict = b) -> list[str]:
            return [v for v in b.get(key, {}).get("value", "").split(";") if v]
        points = []
        for p in get("coords"):
            m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", p)
            if m:
                points.append((float(m.group(2)), float(m.group(1))))
        item = WikidataItem(
            b["item"]["value"].rsplit("/", 1)[-1], b.get("itemLabel", {}).get("value", ""),
            set(get("bmus")), points, [float(w) / 1e6 for w in get("capacity_w")],
            {int(v) for v in get("osm_relations") if v.isdigit()}, set(get("repd_ids")),
            set(get("types")))
        for code in item.bmus:
            by_code[code] = item
    return by_code


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    p1, p2, dp, dl = radians(lat1), radians(lat2), radians(lat2 - lat1), radians(lon2 - lon1)
    return 2 * 6371.0 * asin(sqrt(sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2))


def osm_url(p: Plant) -> str:
    return f"https://www.openstreetmap.org/{p.osm_type}/{p.osm_id}"


def same_entity(item: WikidataItem, row: dict, plant: Plant | None) -> bool:
    """Whether an existing row's farm is the Wikidata item's farm, by an ID or by name."""
    if plant and row.get("osm_url") == osm_url(plant):
        return True
    if row.get("wikidata"):  # the OSM farm's own wikidata tag settles it either way
        return row["wikidata"] == item.qid
    if item.repd_ids & set(re.split(r"[;,\s]+", row.get("repd_id") or "")):
        return True
    return bool(row.get("farm_name")) and name_score(item.label, row["farm_name"]) >= 0.85


def apply_wikidata(units: list[Unit], rows: list[dict], items: dict[str, WikidataItem],
                   plants: list[Plant]) -> Counter:
    """Place GB units that Wikidata links to a farm by their BM unit code. Rows change in place.

    The unit code is an exact key, so it outranks a name match: a Wikidata row replaces the
    existing row unless the existing row is `proposed` and the Wikidata row is not. The point is
    the OpenStreetMap farm the item links to (P402), else an OSM farm tagged with the item, else
    the existing OSM farm when it is the same farm; failing those, the item's own coordinates
    (P625). The Wikidata row is `proposed` when the item is a wind farm with one location and the
    units' summed capacity agrees with one of its capacities (or the OSM farm's); else `review`.
    Supplier units are placed too, unless their National Grid code marks them as an aggregate
    (AG-): Wikidata links most of them to one named farm, so they are not aggregates after all.

    Returns a count of what happened, for the summary.
    """
    by_rel = {p.osm_id: p for p in plants if p.osm_type == "relation"}
    by_qid: dict[str, list[Plant]] = defaultdict(list)
    for p in plants:
        if p.tags.get("wikidata"):
            by_qid[p.tags["wikidata"]].append(p)
    by_url = {osm_url(p): p for p in plants}

    links = {}
    for u in units:
        hits = {items[c].qid: items[c] for c in (u.extra.get("ng_code"), u.unit_id) if c in items}
        if len(hits) == 1:
            links[u.unit_id] = next(iter(hits.values()))
    cap_sum: dict[str, float] = defaultdict(float)
    n_units: Counter = Counter()
    for u in {u.unit_id: u for u in units}.values():  # Elexon lists a few units twice
        if u.unit_id in links:
            n_units[links[u.unit_id].qid] += 1
            cap_sum[links[u.unit_id].qid] += u.capacity_mw or 0.0

    outcome: Counter = Counter()
    for i, (u, r) in enumerate(zip(units, rows, strict=True)):
        item = links.get(u.unit_id)
        if not item:
            continue
        outcome["linked"] += 1
        tag = f"Wikidata links this unit to {item.label} ({item.qid})"
        if u.extra.get("aggregate") and u.extra.get("ng_code", "").startswith("AG-"):
            r["notes"] = "; ".join(filter(None, [r["notes"], tag + ", not placed"]))
            outcome["aggregate kept"] += 1
            continue
        plant = next((by_rel[o] for o in sorted(item.osm_relations) if o in by_rel), None)
        plant = plant or next(iter(by_qid.get(item.qid, [])), None)
        old_plant = by_url.get(r.get("osm_url") or "")
        if not plant and old_plant and same_entity(item, r, None):
            plant = old_plant
        if plant:
            point, source = (plant.lat, plant.lon), "osm"
        elif item.points:
            point, source = item.points[0], "wikidata"
        else:
            r["notes"] = "; ".join(filter(None, [r["notes"], tag + ", which has no location"]))
            outcome["no location"] += 1
            continue

        why = []
        if not item.is_wind:
            why.append(f"Wikidata item is a {' / '.join(sorted(item.types)) or 'thing'}, "
                       "not a wind farm")
        if not plant and len(item.points) > 1:
            why.append(f"Wikidata gives {len(item.points)} coordinates; the first is used")
        farm_caps = item.capacities_mw + ([plant.capacity_mw] if plant and plant.capacity_mw
                                          else [])
        total = cap_sum[item.qid]
        ratios = [total / c for c in farm_caps if c and total]
        if ratios and not any(0.35 <= x <= 1.6 for x in ratios):
            why.append("capacity disagrees")
        status = "review" if why else "proposed"

        had = r.get("lat") not in (None, "") and r["status"] in ("proposed", "review")
        dist = km(point[0], point[1], float(r["lat"]), float(r["lon"])) if had else 0.0
        same = had and same_entity(item, r, plant)
        if RANK.get(status, 0) < RANK.get(r["status"], 0):
            # A proposed link stands against a Wikidata link that has its own doubts.
            where = f", {dist:.0f} km away" if had else ""
            r["notes"] = "; ".join(filter(None, [
                r["notes"], f"{tag}{where}; kept the existing link: {'; '.join(why)}"]))
            outcome["kept existing (Wikidata row would be review)"] += 1
            continue

        notes = [tag]
        if n_units[item.qid] > 1:
            notes.append(f"{n_units[item.qid]} units point at this farm")
        if u.extra.get("aggregate"):
            notes.append("supplier unit, but Wikidata links it to one farm")
        if had and not same:
            notes.append(f"dropped the earlier candidate {r['farm_name']} ({r['status']}, "
                         f"{r['method']}), {dist:.0f} km away")
            outcome["different farm, > 5 km" if dist > AGREE_KM else "different farm, <= 5 km"] += 1
        elif had and dist > AGREE_KM:
            notes.append(f"moved {dist:.0f} km from the earlier {r['location_source']} point "
                         "for the same farm")
            outcome["same farm, moved > 5 km"] += 1
        elif had:
            outcome["same farm, within 5 km"] += 1
        else:
            outcome["newly placed"] += 1
        notes += why
        ratio = min(ratios, key=lambda x: abs(log(x))) if ratios else None
        repd = plant.tags.get("repd:id", "") if plant else ""
        rows[i] = {
            **{k: r[k] for k in ("market", "unit_id", "unit_name", "unit_capacity_mw",
                                 "unit_capacity_kind")},
            "status": status, "method": "wikidata-bmu", "score": 1.0, "location_source": source,
            "farm_name": plant.name if plant else item.label,
            "farm_state": farm_state(plant) if plant else "",
            "farm_capacity_mw": (plant.capacity_mw if plant and plant.capacity_mw
                                 else max(item.capacities_mw, default="")),
            "farm_capacity_ratio": round(ratio, 2) if ratio else "",
            "lat": round(point[0], 5), "lon": round(point[1], 5),
            "osm_url": osm_url(plant) if plant else "",
            "repd_id": repd or ";".join(sorted(item.repd_ids)), "wikidata": item.qid,
            "runner_up": "", "notes": "; ".join(notes),
        }
        outcome[f"-> {status}"] += 1
    return outcome


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    paths = {name: fetch(name, url, args.refresh) for name, url in SOURCES.items()}
    markets = {
        "aemo-nem": (load_aemo(paths["aemo_reg.xlsx"]), "au"),
        "elexon-bm": (load_elexon(paths["elexon_bmunits.json"], load_psd(paths["psd_ids.csv"])),
                      "gb"),
        "ieso": (load_ieso(paths["ieso_cap.xml"]), "on"),
    }
    repd = load_repd(paths["repd.csv"])
    OUT.mkdir(exist_ok=True)
    summary = {}
    for market, (units, area) in markets.items():
        plants = load_plants(fetch_osm(area, args.refresh))
        rows = match_market(units, plants)
        if market == "elexon-bm":
            rows = add_repd_fallback(units, rows, repd)
            check_repd_names(units, rows, repd)
            wd = apply_wikidata(units, rows, load_wikidata(fetch_wikidata(args.refresh)), plants)
            print("  Wikidata BM unit links: "
                  + "  ".join(f"{k} {v}" for k, v in sorted(wd.items())))
        with (OUT / f"{market}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        counts = defaultdict(int)
        for r in rows:
            counts[r["status"]] += 1
        summary[market] = {"units": len(units), "osm_farms": len(plants), **counts}
        print(f"{market:10} units {len(units):4}  OSM farms {len(plants):4}  "
              + "  ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
