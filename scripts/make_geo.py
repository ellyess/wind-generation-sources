"""Make the simplified country outlines the map draws. Run once; the output is committed.

Source: Natural Earth admin-0 countries v5.1.2 (public domain), 1:110m for the world view and
1:50m, cut to a window, for the Europe detail.

    uv run --with shapely python scripts/make_geo.py <ne_110m.geojson> <ne_50m.geojson>
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from shapely.geometry import Polygon, mapping, shape

from wgs.mapdata import EU_LAT0, EU_LON0, europe_frame

OUT = Path(__file__).resolve().parents[1] / "geo"


def laea_inverse(x: float, y: float) -> tuple[float, float]:
    """Unit-sphere Lambert azimuthal equal-area back to lon/lat, about the detail's centre."""
    p0 = math.radians(EU_LAT0)
    rho = math.hypot(x, y)
    if rho == 0:
        return EU_LON0, EU_LAT0
    c = 2 * math.asin(min(rho / 2, 1))
    lat = math.asin(math.cos(c) * math.sin(p0) + y * math.sin(c) * math.cos(p0) / rho)
    den = rho * math.cos(p0) * math.cos(c) - y * math.sin(p0) * math.sin(c)
    lon = math.atan2(x * math.sin(c), den)
    return EU_LON0 + math.degrees(lon), math.degrees(lat)


def europe_window(margin: float = 0.04) -> Polygon:
    """The drawn detail rectangle, with a margin, as a lon/lat polygon to cut outlines to."""
    f = europe_frame()
    w, h = f.width / f.scale, f.height / f.scale
    x0, x1 = f.x0 - margin * w, f.x0 + (1 + margin) * w
    y0, y1 = f.y1 - (1 + margin) * h, f.y1 + margin * h
    n = 80
    ring = ([(x0 + (x1 - x0) * i / n, y0) for i in range(n)]
            + [(x1, y0 + (y1 - y0) * i / n) for i in range(n)]
            + [(x1 - (x1 - x0) * i / n, y1) for i in range(n)]
            + [(x0, y1 - (y1 - y0) * i / n) for i in range(n)])
    return Polygon([laea_inverse(x, y) for x, y in ring])


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


def build(path: str, tolerance: float, window=None, nd: int = 2) -> dict:
    feats = []
    for f in json.loads(Path(path).read_text())["features"]:
        p = f["properties"]
        if p.get("NAME") == "Antarctica":
            continue
        g = shape(f["geometry"])
        if window is not None:
            if not g.intersects(window):
                continue
            g = g.intersection(window)
        g = g.simplify(tolerance, preserve_topology=True)
        if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        feats.append({"type": "Feature",
                      "properties": {"iso": iso(p), "name": p.get("NAME_EN") or p.get("NAME")},
                      "geometry": rounded(mapping(g), nd)})
    return {"type": "FeatureCollection", "features": feats}


def main() -> None:
    small, medium = sys.argv[1], sys.argv[2]
    OUT.mkdir(exist_ok=True)
    note = "Natural Earth admin-0 countries v5.1.2, public domain. Simplified for display."
    for name, data in (("world", build(small, 0.12)),
                       ("europe", build(medium, 0.025, europe_window(), 3))):
        data["source"] = note
        (OUT / f"{name}.geojson").write_text(json.dumps(data, separators=(",", ":")) + "\n")
        print(name, len(data["features"]), (OUT / f"{name}.geojson").stat().st_size)


if __name__ == "__main__":
    main()
