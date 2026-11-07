"""Make the simplified country outlines the map draws. Run once; the output is committed.

Source: Natural Earth admin-0 countries v5.1.2 (public domain), 1:50m, simplified. The page's
map library projects the lon/lat outlines itself.

    uv run --with shapely python scripts/make_geo.py <ne_50m.geojson>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import mapping, shape

OUT = Path(__file__).resolve().parents[1] / "geo"


def iso(props: dict) -> str | None:
    code = props.get("ISO_A2_EH") or props.get("ISO_A2")
    return None if not code or code == "-99" else code


def rounded(geom: dict, nd: int) -> dict:
    def r(c):
        return [round(c[0], nd), round(c[1], nd)]
    coords = geom["coordinates"]
    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": [[r(c) for c in ring] for ring in coords]}
    return {"type": "MultiPolygon",
            "coordinates": [[[r(c) for c in ring] for ring in poly] for poly in coords]}


def build(path: str, tolerance: float, nd: int = 2) -> dict:
    feats = []
    for f in json.loads(Path(path).read_text())["features"]:
        p = f["properties"]
        if p.get("NAME") == "Antarctica":
            continue
        g = shape(f["geometry"]).simplify(tolerance, preserve_topology=True)
        if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        feats.append({"type": "Feature",
                      "properties": {"iso": iso(p), "name": name(p)},
                      "geometry": rounded(mapping(g), nd)})
    return {"type": "FeatureCollection", "features": feats}


# Grouped with Europe because ENTSO-E and Eurostat report them; Natural Earth puts them in Asia.
EUROPE_OVERRIDE = {"TR", "CY", "GE", "AM", "AZ"}


def continent(props: dict) -> str:
    code, name = iso(props), props.get("CONTINENT", "")
    if code in EUROPE_OVERRIDE:
        return "Europe"
    if name in ("North America", "South America"):
        return "Americas"
    if name.startswith("Seven seas"):
        name = props.get("REGION_UN", "")
        return "Americas" if name == "Americas" else name
    return name


# ISO codes that global datasets use but Natural Earth folds into another country.
EXTRA_PLACES = {
    "AQ": {"name": "Antarctica", "continent": "Antarctica"},
    "BQ": {"name": "Bonaire, Sint Eustatius and Saba", "continent": "Americas"},
    "GP": {"name": "Guadeloupe", "continent": "Americas"},
    "MQ": {"name": "Martinique", "continent": "Americas"},
    "RE": {"name": "Réunion", "continent": "Africa"},
    "GF": {"name": "French Guiana", "continent": "Americas"},
    "YT": {"name": "Mayotte", "continent": "Africa"},
    "TK": {"name": "Tokelau", "continent": "Oceania"},
}


# Short names people search for, where Natural Earth's long form is formal.
NAME_OVERRIDE = {"KR": "South Korea", "KP": "North Korea", "RU": "Russia", "CZ": "Czechia",
                 "LA": "Laos", "SY": "Syria", "MD": "Moldova", "BN": "Brunei"}


def name(props: dict) -> str:
    return NAME_OVERRIDE.get(iso(props) or "") or props.get("NAME_LONG") or props.get("NAME") or ""


def places(path: str) -> dict:
    """Name and continent for every country Natural Earth codes, for the index and the search.

    Several features can share a code (Australia and the Ashmore and Cartier Islands are both
    AU), so the largest one names it.
    """
    out, size = {}, {}
    for f in json.loads(Path(path).read_text())["features"]:
        p = f["properties"]
        code = iso(p)
        if not code or p.get("NAME") == "Antarctica":
            continue
        area = shape(f["geometry"]).area
        if area > size.get(code, -1):
            size[code] = area
            out[code] = {"name": name(p), "continent": continent(p)}
    for code, place in EXTRA_PLACES.items():
        out.setdefault(code, place)
    return dict(sorted(out.items()))


def main() -> None:
    medium = sys.argv[1]
    OUT.mkdir(exist_ok=True)
    note = "Natural Earth admin-0 countries v5.1.2, public domain. Simplified for display."
    data = build(medium, 0.02, 3)
    data["source"] = note
    path = OUT / "countries.geojson"
    path.write_text(json.dumps(data, separators=(",", ":")) + "\n")
    print("countries", len(data["features"]), path.stat().st_size)
    table = {"source": note, "places": places(medium)}
    (OUT / "places.json").write_text(json.dumps(table, ensure_ascii=False, indent=0) + "\n")
    print("places", len(table["places"]))


if __name__ == "__main__":
    main()
