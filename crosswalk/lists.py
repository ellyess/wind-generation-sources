"""Place the units in `crosswalk/units/*.csv` on the map.

Each unit list names the wind plants one catalogue entry publishes output for (format in
`units/README.md`). Rows that carry the publisher's own coordinates are kept as they are, with
status `published`. The rest are matched by name and capacity to OpenStreetMap wind farms in the
row's `area`, using the same rules as `build.py`, and get `proposed`, `review` or `unmatched`.

    uv run python crosswalk/lists.py              # all lists; OSM areas are cached
    uv run python crosswalk/lists.py --refresh    # fetch the OSM areas again
    uv run python crosswalk/lists.py br-ons-capacity-factor   # one list

Writes `output/<entry-id>.csv` in build.py's columns plus `entry`, and `output/lists.json`.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNITS = HERE / "units"
_spec = importlib.util.spec_from_file_location("crosswalk_build", HERE / "build.py")
assert _spec and _spec.loader
cb = importlib.util.module_from_spec(_spec)
sys.modules["crosswalk_build"] = cb
_spec.loader.exec_module(cb)

# Offshore farms beyond territorial waters fall outside a country's area: add them by box.
OFFSHORE_BOX = {
    "TW": "(21.5,118.8,26.5,122.8)", "KR": "(32.8,124.0,38.8,131.5)",
    "DE": "(53.2,3.3,55.4,14.6)", "IE": "(51.0,-11.5,55.6,-5.3)", "FR": "(42.0,-5.5,51.5,9.6)",
}
FIELDS = ["entry", *cb.FIELDS]

# Words that say "wind farm" or "company" in the other languages of these markets.
cb.STOP |= {
    "parque", "eolico", "eolica", "eolicos", "eolicas", "central", "centrale", "usina", "uee",
    "eol", "eolienne", "eoliennes", "eolien", "parc", "complexo", "complejo", "windpark",
    "windkraft", "windenergie", "vindkraft", "vindpark", "vindkraftverk", "aiolikos", "aioliko",
    "sa", "ltda", "spa", "srl", "gmbh", "ag", "kg", "co", "as", "de", "del", "la", "el", "do", "da",
    "dos", "das", "pe", "cge", "wpp", "wf", "res", "energia", "energias", "ventos", "vento",
}


def fetch_area(area: str, refresh: bool) -> list[dict]:
    key = "ISO3166-2" if "-" in area else "ISO3166-1"
    sel = 'nwr["power"="plant"]["plant:source"~"wind"]'
    extra = ""
    if area in OFFSHORE_BOX:
        box = OFFSHORE_BOX[area]
        extra = f'{sel}["offshore"="yes"]{box};{sel}[name~"[Oo]ffshore"]{box};'
    query = (f'[out:json][timeout:180];area["{key}"="{area}"][admin_level]->.a;'
             f'({sel}(area.a);nwr["construction:power"="plant"]["construction:plant:source"~"wind"]'
             f'(area.a);{extra});out center tags;')
    data = urllib.parse.urlencode({"data": query}).encode()
    name = f"osm_plants_list_{area.lower()}.json"
    cached = (cb.CACHE / name).exists()
    path = cb.fetch(name, cb.OVERPASS, refresh, data)
    if not cached or refresh:
        time.sleep(2)  # be gentle with the public Overpass servers
    return json.loads(path.read_text())["elements"]


def read_list(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("unit_id") or "").strip()]


def number(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def place(entry: str, rows: list[dict], refresh: bool) -> list[dict]:
    out: list[dict] = []
    by_area: dict[str, list] = defaultdict(list)
    for r in rows:
        lat, lon = number(r.get("lat")), number(r.get("lon"))
        names = [r.get("unit_name") or "", *(r.get("alt_names") or "").split(";")]
        names = [n.strip() for n in names if n.strip()] or [r["unit_id"]]
        if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            out.append({
                "entry": entry, "market": entry, "unit_id": r["unit_id"],
                "unit_name": names[0], "unit_capacity_mw": number(r.get("capacity_mw")),
                "unit_capacity_kind": "registered", "status": "published",
                "method": "publisher", "location_source": "publisher", "farm_name": names[0],
                "lat": round(lat, 5), "lon": round(lon, 5), "notes": r.get("notes", ""),
            })
            continue
        area = (r.get("area") or "").strip().upper()
        unit = cb.Unit(entry, r["unit_id"], names, number(r.get("capacity_mw")),
                       "registered", {"notes": r.get("notes", "")})
        by_area[area].append(unit)
    for area, units in by_area.items():
        if not area:
            out += [{"entry": entry, "market": entry, "unit_id": u.unit_id,
                     "unit_name": u.names[0], "status": "unmatched", "notes": "no area given"}
                    for u in units]
            continue
        try:
            plants = cb.load_plants(fetch_area(area, refresh))
        except OSError as exc:
            print(f"  {entry}: OpenStreetMap query for {area} failed: {exc}", file=sys.stderr)
            plants = []
        for row in cb.match_market(units, plants):
            row["entry"] = entry
            demote(row)
            out.append(row)
    return out


def demote(row: dict) -> None:
    """Stricter than build.py, since these lists are longer and their names noisier.

    A proposed link needs a distinctive word shared with the farm's name (a near-identical
    spelling alone, "Nelson" against "Neilston", is not enough), and the unit's own capacity
    must not be far from the farm's, whatever other units point at the same farm.
    """
    if row.get("status") != "proposed" or row.get("method") != "name":
        return
    farm = set(cb.tokens(row.get("farm_name") or ""))
    unit = {t for n in (row.get("unit_name") or "").split(";") for t in cb.tokens(n)}
    reasons = []
    if not (farm & unit) - cb.GENERIC:
        reasons.append("no distinctive word shared")
    # Stage codes ("2a" against "2b and 4") must agree where both names carry one.
    fd, ud = {t for t in farm if any(c.isdigit() for c in t)}, {
        t for t in unit if any(c.isdigit() for c in t)}
    if fd and ud and not fd & ud:
        reasons.append("stage numbers differ")
    cap, farm_cap = number(str(row.get("unit_capacity_mw") or "")), number(
        str(row.get("farm_capacity_mw") or ""))
    if cap and farm_cap and not 0.1 <= cap / farm_cap <= 1.6:
        reasons.append("unit capacity far from the farm's")
    if reasons:
        row["status"] = "review"
        row["notes"] = "; ".join(filter(None, [row.get("notes", ""), *reasons]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("entries", nargs="*", help="entry ids (default: every list)")
    ap.add_argument("--refresh", action="store_true", help="fetch the OSM areas again")
    args = ap.parse_args()
    paths = sorted(UNITS.glob("*.csv"))
    if args.entries:
        paths = [p for p in paths if p.stem in args.entries]
    cb.OUT.mkdir(exist_ok=True)
    summary_path = cb.OUT / "lists.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    for path in paths:
        rows = place(path.stem, read_list(path), args.refresh)
        with (cb.OUT / f"{path.stem}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        counts = Counter(r["status"] for r in rows)
        summary[path.stem] = {"units": len(rows), **dict(sorted(counts.items()))}
        print(f"{path.stem:46} " + "  ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    summary_path.write_text(json.dumps(dict(sorted(summary.items())), indent=2) + "\n")


if __name__ == "__main__":
    main()
