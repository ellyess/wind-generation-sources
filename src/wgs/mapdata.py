"""The map's data: country outlines and the farms the crosswalk links to published units.

Outlines stay in lon/lat; the page's map library projects them.
"""

from __future__ import annotations

import csv
import json
import shutil
from functools import cache
from pathlib import Path

from wgs.catalogue import ROOT, SOURCES_DIR, parse_entry

GEO = ROOT / "geo"
CROSSWALK = ROOT / "crosswalk" / "output"

# Market file -> the catalogue entry that publishes those units' output.
MARKET_ENTRY = {
    "aemo-nem": "au-aemo-nem-unit-scada",
    "elexon-bm": "gb-elexon-bmrs-unit-output",
    "ieso": "ca-on-ieso-generator-output",
    # Locations the publisher gives itself (crosswalk/registers.py), not matched by name.
    "ens-dk": "dk-ens-turbine-register",
    "eia-860": "us-eia-923-plant-generation",
}


# Year of the Code-Point Open release behind the postcode points (its Doc/licence.txt).
CODEPOINT_YEAR = 2026

# Entries whose register gives one point per turbine; drawn smaller on the map.
TURBINE_POINTS = {"dk-ens-turbine-register", "de-netztransparenz-eeg-movement-data"}

# Entries whose units at one point nest (Brazil's ONS lists complexes and the plants inside them
# at the same collector substation), so a point's capacity is its largest unit, not the sum.
NESTED_UNITS = {"br-ons-capacity-factor", "br-ons-generation-by-plant-hourly"}


def _rows() -> list[tuple[str, dict]]:
    """(entry, row) for every crosswalk output: the matched markets and the unit lists."""
    out = []
    for path in sorted(CROSSWALK.glob("*.csv")):
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                entry = row.get("entry") or MARKET_ENTRY.get(path.stem)
                if entry:
                    out.append((entry, row))
    return out


def _mw(value: str | None) -> float | None:
    """A capacity in MW from a crosswalk cell, or None when it is blank, zero or unreadable."""
    try:
        mw = float(value or "")
    except ValueError:
        return None
    return mw if mw > 0 else None


@cache
def _entry_countries(entry: str) -> tuple[str, ...]:
    path = SOURCES_DIR / f"{entry}.yaml"
    if not path.exists():
        return ()
    return tuple(parse_entry(path.read_text(encoding="utf-8")).get("countries") or ())


@cache
def _outlines() -> dict[str, list[list[list[float]]]]:
    """Each country's outer rings, for placing a point of a multi-country entry."""
    data = json.loads((GEO / "countries.geojson").read_text(encoding="utf-8"))
    out: dict[str, list] = {}
    for f in data["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        out[f["properties"]["iso"]] = [p[0] for p in polys]
    return out


def _inside(lon: float, lat: float, ring: list[list[float]]) -> bool:
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def _country_of(lat: float, lon: float, codes: tuple[str, ...]) -> str:
    """Which of an entry's countries a point falls in; offshore points take the nearest coast."""
    rings = _outlines()
    for c in codes:
        if any(_inside(lon, lat, r) for r in rings.get(c, [])):
            return c
    def gap(c: str) -> float:
        return min(((x - lon) ** 2 + (y - lat) ** 2 for r in rings.get(c, []) for x, y in r),
                   default=float("inf"))
    return min(codes, key=gap)


def build_farms() -> dict:
    """Farms or turbines whose output is published per unit, with a location.

    Name matches contribute proposed links only; registers and publishers' own files contribute
    their locations (status "published"). Stations placed at their postcode's centroid (status
    "approximate", located by "os-codepoint-open") are drawn too, marked as approximate.

    `mw` is the summed capacity of the units behind a point (capped at the matched farm's own
    capacity, which stands in when no unit gives one); it is left out when neither does. `iso`
    names the country only for entries that span several.
    """
    farm_mw: dict[str, float] = {}
    farms: dict[str, dict] = {}
    for entry, row in _rows():
        if row.get("status") not in ("proposed", "published", "approximate") or not row.get("lat"):
            continue
        lat, lon = float(row["lat"]), float(row["lon"])
        key = (row.get("osm_url") or f"{lat:.4f},{lon:.4f}") + "|" + entry
        unit_name = row.get("unit_name") or ""
        osm_name = (row.get("farm_name") or "").split(";")[0].strip()
        name = osm_name or ("" if unit_name.startswith("(") else unit_name)
        farm = farms.setdefault(key, {
            "name": name or row["unit_id"],
            "entry": entry, "n": 0, "lat": round(lat, 4), "lon": round(lon, 4),
            "located_by": row.get("location_source") or "osm",
        })
        if row.get("osm_url"):
            farm["osm"] = row["osm_url"]
        if entry in TURBINE_POINTS:
            farm["turbine"] = True
        farm["n"] += 1  # units behind this point; the unit ids are in crosswalk/output
        if (mw := _mw(row.get("unit_capacity_mw"))) is not None:
            old = farm.get("mw", 0)
            farm["mw"] = max(old, mw) if entry in NESTED_UNITS else old + mw
        if key not in farm_mw and (mw := _mw(row.get("farm_capacity_mw"))) is not None:
            farm_mw[key] = mw
    for key, farm in farms.items():
        # Registered unit capacities can overstate a farm (GB's BM units); the farm's own
        # figure caps the sum where there is one.
        if key in farm_mw:
            farm["mw"] = min(farm.get("mw", farm_mw[key]), farm_mw[key])
        if "mw" in farm:
            farm["mw"] = round(farm["mw"], 2 if farm["mw"] < 10 else 1)
        if len(codes := _entry_countries(farm["entry"])) > 1:
            farm["iso"] = _country_of(farm["lat"], farm["lon"], codes)
    used = {f["located_by"] for f in farms.values()}
    parts = ["Farm locations matched by name are derived from OpenStreetMap "
             "(© OpenStreetMap contributors, ODbL)"]
    if "repd" in used:
        parts.append("in Great Britain, where OpenStreetMap has no farm, the Renewable Energy "
                     "Planning Database (contains public sector information licensed under the "
                     "Open Government Licence v3.0)")
    if "wikidata" in used:
        parts.append("in Great Britain, links from balancing mechanism units to farms, and some "
                     "farm points, from Wikidata (CC0)")
    if "ens" in used:
        parts.append("Danish turbine locations from the Danish Energy Agency (Energistyrelsen) "
                     "turbine register (https://ens.dk/media/4945/download), converted from "
                     "ETRS89 / UTM 32N to latitude and longitude and otherwise as published")
    if "eia-860" in used:
        parts.append("US plant locations from EIA-860 (U.S. Energy Information Administration)")
    if any(f["entry"] == "de-netztransparenz-eeg-movement-data" for f in farms.values()):
        parts.append("German turbine locations from the Bundesnetzagentur Marktstammdatenregister "
                     "(Data licence Germany, attribution, version 2.0)")
    if "os-codepoint-open" in used:
        parts.append("in Great Britain, stations with no confident farm match are placed at "
                     "their postcode's centroid, not at the turbine, from Ordnance Survey "
                     "Code-Point Open under the Open Government Licence v3.0 (Contains OS data "
                     "© Crown copyright "
                     f"and database right {CODEPOINT_YEAR}; Contains Royal Mail data © Royal Mail "
                     f"copyright and database right {CODEPOINT_YEAR}; Contains National Statistics "
                     f"data © Crown copyright and database right {CODEPOINT_YEAR})")
    if "publisher" in used:
        parts.append("elsewhere, locations published by the source's own publisher")
    return {
        "licence": "; ".join(parts) + ". Links matched by name are unreviewed proposals.",
        "farms": sorted(farms.values(), key=lambda f: f["name"] or ""),
    }


def columnar(data: dict) -> dict:
    """The farm points as parallel columns, which is a fraction of the size of 40,000 objects.

    `entry` and `located_by` hold indices into `entries` and `located`; a missing value is null.
    The site turns the columns back into one object per point.
    """
    farms = data["farms"]
    entries = sorted({f["entry"] for f in farms})
    located = sorted({f["located_by"] for f in farms})
    e_ix = {e: i for i, e in enumerate(entries)}
    l_ix = {k: i for i, k in enumerate(located)}
    return {
        "licence": data["licence"], "entries": entries, "located": located, "count": len(farms),
        "cols": {
            "name": [f["name"] for f in farms],
            "entry": [e_ix[f["entry"]] for f in farms],
            "n": [f["n"] for f in farms],
            "lat": [f["lat"] for f in farms],
            "lon": [f["lon"] for f in farms],
            "located_by": [l_ix[f["located_by"]] for f in farms],
            "turbine": [1 if f.get("turbine") else 0 for f in farms],
            "mw": [f.get("mw") for f in farms],
            "osm": [f.get("osm") for f in farms],
            "iso": [f.get("iso") for f in farms],
        },
    }


def write_map(out: Path) -> None:
    shutil.copy2(GEO / "countries.geojson", out / "countries.geojson")
    (out / "farms.json").write_text(json.dumps(columnar(build_farms()), ensure_ascii=False,
                                               separators=(",", ":")), encoding="utf-8")
