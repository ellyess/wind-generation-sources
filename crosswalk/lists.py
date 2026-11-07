"""Place the units in `crosswalk/units/*.csv` on the map.

Each unit list names the wind plants one catalogue entry publishes output for (format in
`units/README.md`). Rows that carry the publisher's own coordinates are kept as they are, with
status `published`. The rest are matched by name and capacity to OpenStreetMap wind farms in the
row's `area`, using the same rules as `build.py`, and get `proposed`, `review` or `unmatched`.

    uv run python crosswalk/lists.py              # all lists; OSM areas are cached
    uv run python crosswalk/lists.py --refresh    # fetch the OSM areas again
    uv run python crosswalk/lists.py br-ons-capacity-factor   # one list

Writes `output/<entry-id>.csv` in build.py's columns plus `entry`, and `output/lists.json`.

Great Britain rows that give a postcode (a `postcode` column, or "station postcode X (" in
`notes`) and find no confident OpenStreetMap farm are placed at that postcode's centroid from
Ordnance Survey Code-Point Open, with status `approximate` (see `postcode_fallback`).
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import re
import sys
import time
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from math import asin, cos, radians, sin, sqrt
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


# ---------- postcode fallback (Great Britain) ----------

# Ordnance Survey Code-Point Open: one centroid per current GB postcode unit, in British National
# Grid. Open Government Licence v3.0, downloaded without a key from the OS Downloads API. It has no
# Northern Ireland (BT) postcodes, and positional quality 90 means "no coordinates" (0, 0).
CODEPOINT = ("codepo_gb.zip", "https://api.os.uk/downloads/v1/products/CodePointOpen/downloads"
             "?area=GB&format=CSV&redirect")
POSTCODE_IN_NOTES = re.compile(r"station postcode (.+?) \(", re.I)
POSTCODE_SHAPE = re.compile(r"^[A-Z]{1,2}[0-9][A-Z0-9]?[0-9][A-Z]{2}$")
# An OSM candidate under review counts as confirmed by the postcode when it lies this close to the
# centroid: about the 90th percentile of the distance for onshore links already proposed.
NEAR_KM = 5.0
# A proposed onshore link this far from the station's postcode gets a note for a reviewer.
FLAG_KM = 20.0


def norm_postcode(text: str) -> str:
    return re.sub(r"\s+", "", text or "").upper()


def unit_postcode(row: dict) -> str:
    """The postcode a unit list gives for a row: its `postcode` column, else from `notes`."""
    if (row.get("postcode") or "").strip():
        return norm_postcode(row["postcode"])
    m = POSTCODE_IN_NOTES.search(row.get("notes") or "")
    return norm_postcode(m.group(1)) if m else ""


def is_offshore(unit: dict) -> bool:
    return "offshore" in f"{unit.get('notes', '')} {unit.get('unit_name', '')}".lower()


def load_codepoint(refresh: bool, wanted: set[str]) -> dict[str, tuple[int, float, float]]:
    """Postcode (no spaces) -> (positional quality, latitude, longitude), for the wanted ones."""
    path = cb.fetch(CODEPOINT[0], CODEPOINT[1], refresh)
    out = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not (name.startswith("Data/CSV/") and name.endswith(".csv")):
                continue
            for r in csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8")):
                pc = norm_postcode(r[0])
                if pc not in wanted:
                    continue
                quality, east, north = int(r[1]), float(r[2]), float(r[3])
                if quality >= 90 or not (east or north):
                    continue
                out[pc] = (quality, *cb.bng_to_wgs84(east, north))
    return out


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2, dp, dl = radians(lat1), radians(lat2), radians(lat2 - lat1), radians(lon2 - lon1)
    return 2 * 6371.0 * asin(sqrt(sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2))


def capacity_agrees(row: dict) -> bool:
    """The unit's capacity (summed over units sharing the farm) does not contradict the farm's."""
    ratio = number(str(row.get("farm_capacity_ratio") or ""))
    if ratio is None:
        cap = number(str(row.get("unit_capacity_mw") or ""))
        farm = number(str(row.get("farm_capacity_mw") or ""))
        ratio = cap / farm if cap and farm else None
    return ratio is None or 0.35 <= ratio <= 1.6


def postcode_fallback(rows: list[dict], units: dict[str, dict],
                      codepoint: dict[str, tuple[int, float, float]]) -> None:
    """Place GB rows without a confident OSM farm at their postcode's centroid, in place.

    A postcode centroid is where the postcode's addresses sit, not the turbine: on a farm it is
    usually the farmhouse or the site entrance. So:
    - `proposed` and `published` rows keep their location. A proposed onshore link more than
      FLAG_KM from the postcode gets a note.
    - A `review` row whose OSM farm lies within NEAR_KM of the centroid, with capacities that do
      not disagree, is confirmed: it becomes `proposed` by method `<method>+postcode`.
    - Any other `review` or `unmatched` row with a GB postcode is placed at the centroid: status
      `approximate`, method `postcode`, location_source `os-codepoint-open`. The OSM candidate
      under review, if any, is named in the notes with its distance.
    - Offshore stations are skipped: their registered postcode is an onshore office or substation.
    """
    for row in rows:
        unit = units.get(row["unit_id"], {})
        pc = unit_postcode(unit)
        if (unit.get("area") or "").upper() != "GB" or not pc:
            continue
        hit = codepoint.get(pc)
        has_point = row.get("lat") not in (None, "")
        dist = (km(hit[1], hit[2], float(row["lat"]), float(row["lon"]))
                if hit and has_point else None)
        if row["status"] in ("proposed", "published"):
            if dist is not None and dist > FLAG_KM and not is_offshore(unit):
                row["notes"] = "; ".join(filter(None, [
                    row.get("notes"), f"check: station postcode is {dist:.0f} km from this farm"]))
            continue
        if row["status"] not in ("review", "unmatched") or not hit or is_offshore(unit):
            continue
        if (row["status"] == "review" and dist is not None and dist <= NEAR_KM
                and capacity_agrees(row)):
            row["status"] = "proposed"
            row["method"] = f"{row.get('method') or 'name'}+postcode"
            row["notes"] = "; ".join(filter(None, [
                row.get("notes"), f"station postcode centroid {dist:.1f} km away confirms it"]))
            continue
        before = ""
        if row["status"] == "review" and row.get("farm_name") and dist is not None:
            before = f"OSM candidate {row['farm_name']} (review) is {dist:.1f} km away"
        quality, lat, lon = hit
        names = [n.strip() for n in (row.get("unit_name") or "").split(";") if n.strip()]
        for key in ("score", "farm_state", "farm_capacity_mw", "farm_capacity_ratio", "osm_url",
                    "repd_id", "wikidata", "runner_up"):
            row[key] = ""
        row.update({
            "status": "approximate", "method": "postcode", "location_source": "os-codepoint-open",
            "farm_name": names[0] if names else row["unit_id"],
            "lat": round(lat, 5), "lon": round(lon, 5),
            "notes": "; ".join(filter(None, [
                f"placed at the station's postcode centroid ({pc[:-3]} {pc[-3:]}, Code-Point Open "
                f"positional quality {quality}), not at the turbine", before])),
        })


def unplaced_postcodes(rows: list[dict], units: dict[str, dict],
                       codepoint: dict[str, tuple[int, float, float]]) -> Counter:
    """Why rows that are still not on the map got no postcode point."""
    why: Counter = Counter()
    for row in rows:
        if row["status"] not in ("review", "unmatched"):
            continue
        unit = units.get(row["unit_id"], {})
        pc = unit_postcode(unit)
        if not pc:
            why["no postcode"] += 1
        elif pc.startswith("BT"):
            why["Northern Ireland postcode (not in Code-Point Open)"] += 1
        elif is_offshore(unit):
            why["offshore (postcode is onshore)"] += 1
        elif not POSTCODE_SHAPE.match(pc):
            why["malformed postcode"] += 1
        elif pc not in codepoint:
            why["postcode not in Code-Point Open (terminated or mistyped)"] += 1
        else:
            why["other"] += 1
    return why


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
        units = read_list(path)
        rows = place(path.stem, units, args.refresh)
        by_id = {u["unit_id"]: u for u in units}
        wanted = {unit_postcode(u) for u in units if (u.get("area") or "").upper() == "GB"} - {""}
        if wanted:
            codepoint = load_codepoint(args.refresh, wanted)
            postcode_fallback(rows, by_id, codepoint)
            for why, n in sorted(unplaced_postcodes(rows, by_id, codepoint).items()):
                print(f"  {path.stem}: {n} not placed by postcode: {why}")
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
