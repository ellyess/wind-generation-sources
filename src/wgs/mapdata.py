"""The map's data: country outlines and the farms the crosswalk links to published units.

Outlines stay in lon/lat; the page's map library projects them.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from wgs.catalogue import ROOT

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


# Entries whose register gives one point per turbine; drawn smaller on the map.
TURBINE_POINTS = {"dk-ens-turbine-register", "de-netztransparenz-eeg-movement-data"}


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


def build_farms() -> dict:
    """Farms or turbines whose output is published per unit, with a location.

    Name matches contribute proposed links only; registers and publishers' own files contribute
    their locations (status "published").
    """
    farms: dict[str, dict] = {}
    for entry, row in _rows():
        if row.get("status") not in ("proposed", "published") or not row.get("lat"):
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
    used = {f["located_by"] for f in farms.values()}
    parts = ["Farm locations matched by name are derived from OpenStreetMap "
             "(© OpenStreetMap contributors, ODbL)"]
    if "repd" in used:
        parts.append("in Great Britain, where OpenStreetMap has no farm, the Renewable Energy "
                     "Planning Database (contains public sector information licensed under the "
                     "Open Government Licence v3.0)")
    if "ens" in used:
        parts.append("Danish turbine locations from the Danish Energy Agency (Energistyrelsen) "
                     "turbine register (https://ens.dk/media/4945/download), converted from "
                     "ETRS89 / UTM 32N to latitude and longitude and otherwise as published")
    if "eia-860" in used:
        parts.append("US plant locations from EIA-860 (U.S. Energy Information Administration)")
    if any(f["entry"] == "de-netztransparenz-eeg-movement-data" for f in farms.values()):
        parts.append("German turbine locations from the Bundesnetzagentur Marktstammdatenregister "
                     "(Data licence Germany, attribution, version 2.0)")
    if "publisher" in used:
        parts.append("elsewhere, locations published by the source's own publisher")
    return {
        "licence": "; ".join(parts) + ". Links matched by name are unreviewed proposals.",
        "farms": sorted(farms.values(), key=lambda f: f["name"] or ""),
    }


def write_map(out: Path) -> None:
    shutil.copy2(GEO / "countries.geojson", out / "countries.geojson")
    (out / "farms.json").write_text(json.dumps(build_farms(), ensure_ascii=False,
                                               separators=(",", ":")), encoding="utf-8")
