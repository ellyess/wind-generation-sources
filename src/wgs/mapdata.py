"""Project the country outlines and crosswalk farms into the two map views.

View 1 is the world in Equal Earth; Detail A is Europe in Lambert azimuthal equal-area. Both
are equal-area, so shaded countries are compared at their true relative size. Projection runs
at build time and the page receives finished SVG paths.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from wgs.catalogue import ROOT

GEO = ROOT / "geo"
CROSSWALK = ROOT / "crosswalk" / "output"

# Market file -> the catalogue entry that publishes those units' output.
MARKET_ENTRY = {
    "aemo-nem": "au-aemo-nem-unit-scada",
    "elexon-bm": "gb-elexon-bmrs-unit-output",
    "ieso": "ca-on-ieso-generator-output",
}

# Europe detail: centre of the projection and the lon/lat window drawn.
EU_LON0, EU_LAT0 = 10.0, 52.0
EU_WINDOW = (-25.0, 34.0, 45.0, 71.5)
WORLD_LAT = (-57.0, 84.0)
WORLD_WIDTH, EU_WIDTH = 1000.0, 560.0

_A1, _A2, _A3, _A4 = 1.340264, -0.081106, 0.000893, 0.003796
_M = math.sqrt(3) / 2


def equal_earth(lon: float, lat: float) -> tuple[float, float]:
    """Equal Earth (Šavrič, Patterson and Jenny 2018), unit sphere, y up."""
    lam, phi = math.radians(lon), math.radians(lat)
    th = math.asin(_M * math.sin(phi))
    t2 = th * th
    t6 = t2 * t2 * t2
    x = (2 * math.sqrt(3) * lam * math.cos(th)
         / (3 * (9 * _A4 * t6 * t2 + 7 * _A3 * t6 + 3 * _A2 * t2 + _A1)))
    y = th * (_A1 + _A2 * t2 + t6 * (_A3 + _A4 * t2))
    return x, y


def laea(lon: float, lat: float,
         lon0: float = EU_LON0, lat0: float = EU_LAT0) -> tuple[float, float]:
    """Lambert azimuthal equal-area on the unit sphere, y up."""
    lam, phi = math.radians(lon - lon0), math.radians(lat)
    p0 = math.radians(lat0)
    denom = 1 + math.sin(p0) * math.sin(phi) + math.cos(p0) * math.cos(phi) * math.cos(lam)
    k = math.sqrt(2 / max(denom, 1e-12))
    return (k * math.cos(phi) * math.sin(lam),
            k * (math.cos(p0) * math.sin(phi) - math.sin(p0) * math.cos(phi) * math.cos(lam)))


class Frame:
    """Maps projected unit-sphere coordinates into an SVG box of a given width, y down."""

    def __init__(self, project, corners: list[tuple[float, float]], width: float, pad: float = 0):
        self.project = project
        xs, ys = zip(*(project(lo, la) for lo, la in corners), strict=True)
        self.x0, self.y1 = min(xs), max(ys)
        self.scale = width / (max(xs) - self.x0)
        self.width = width
        self.height = (self.y1 - min(ys)) * self.scale
        self.pad = pad

    def xy(self, lon: float, lat: float) -> tuple[float, float]:
        x, y = self.project(lon, lat)
        return (x - self.x0) * self.scale, (self.y1 - y) * self.scale

    @property
    def view_box(self) -> str:
        return f"0 0 {self.width:.0f} {self.height:.0f}"


def _edge(lon0, lat0, lon1, lat1, n=60):
    return [(lon0 + (lon1 - lon0) * i / n, lat0 + (lat1 - lat0) * i / n) for i in range(n + 1)]


def world_frame() -> Frame:
    lo, hi = WORLD_LAT
    corners = (_edge(-180, lo, 180, lo) + _edge(-180, hi, 180, hi)
               + _edge(-180, lo, -180, hi) + _edge(180, lo, 180, hi))
    return Frame(equal_earth, corners, WORLD_WIDTH)


def europe_frame() -> Frame:
    w, s, e, n = EU_WINDOW
    # The drawn window is the projected box of the lon/lat window's edges.
    corners = _edge(w, s, e, s) + _edge(w, n, e, n) + _edge(w, s, w, n) + _edge(e, s, e, n)
    return Frame(laea, corners, EU_WIDTH)


def _path(geom: dict, frame: Frame) -> str:
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    parts = []
    for poly in polys:
        for ring in poly:
            pts = [frame.xy(lo, la) for lo, la in ring]
            out, last = [], None
            for x, y in pts:
                cell = (round(x, 1), round(y, 1))
                if cell != last:
                    out.append(f"{cell[0]:g},{cell[1]:g}")
                    last = cell
            if len(out) >= 3:
                parts.append("M" + "L".join(out) + "Z")
    return "".join(parts)


def _view(name: str, frame: Frame) -> dict:
    data = json.loads((GEO / f"{name}.geojson").read_text())
    countries = []
    for f in data["features"]:
        lat_max = max(c[1] for c in _coords(f["geometry"]))
        if name == "world" and lat_max < WORLD_LAT[0]:
            continue
        d = _path(f["geometry"], frame)
        if d:
            props = f["properties"]
            countries.append({"iso": props["iso"], "name": props["name"], "d": d})
    return {"viewBox": frame.view_box, "countries": countries}


def _coords(geom: dict):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        for ring in poly:
            yield from ring


def _line(points, frame: Frame) -> str:
    out = [frame.xy(lo, la) for lo, la in points]
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in out)


def _graticule(frame: Frame, lons, lats, lon_span, lat_span) -> str:
    parts = [_line(_edge(lo, lat_span[0], lo, lat_span[1]), frame) for lo in lons]
    parts += [_line(_edge(lon_span[0], la, lon_span[1], la, n=120), frame) for la in lats]
    return "".join(parts)


def build_map() -> dict:
    world, europe = world_frame(), europe_frame()
    w, s, e, n = EU_WINDOW
    lo, hi = WORLD_LAT
    window = _edge(w, s, e, s) + _edge(e, s, e, n) + _edge(e, n, w, n) + _edge(w, n, w, s)
    edge = _edge(-180, lo, 180, lo) + _edge(180, lo, 180, hi) + _edge(180, hi, -180, hi) + _edge(
        -180, hi, -180, lo)
    corner = [round(v, 1) for v in world.xy(w, n)]
    world_grid = _graticule(world, range(-150, 180, 30), (-30, 0, 30, 60), (-180, 180), WORLD_LAT)
    europe_grid = _graticule(europe, range(-30, 60, 10), range(30, 80, 10), (-40, 60), (25, 80))
    return {
        "source": "Country outlines: Natural Earth (public domain).",
        "world": {
            **_view("world", world),
            "frame": _line(edge, world) + "Z",
            "graticule": world_grid,
        },
        "europe": {
            **_view("europe", europe),
            "graticule": europe_grid,
        },
        "detail": {"d": _line(window, world) + "Z", "label": corner},
    }


def build_farms() -> dict:
    """Farms the crosswalk links to units with published output. Proposed links only."""
    world, europe = world_frame(), europe_frame()
    w, s, e, n = EU_WINDOW
    farms: dict[str, dict] = {}
    for market, entry in MARKET_ENTRY.items():
        path = CROSSWALK / f"{market}.csv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("status") != "proposed" or not row.get("lat"):
                    continue
                lat, lon = float(row["lat"]), float(row["lon"])
                key = row.get("osm_url") or f"{market}:{lat:.4f},{lon:.4f}"
                unit_name = row.get("unit_name") or ""
                osm_name = (row.get("farm_name") or "").split(";")[0].strip()
                name = osm_name or ("" if unit_name.startswith("(") else unit_name)
                farm = farms.setdefault(key, {
                    "name": name or row["unit_id"],
                    "entry": entry, "units": [], "lat": round(lat, 4), "lon": round(lon, 4),
                    "osm": row.get("osm_url", ""),
                    "located_by": row.get("location_source") or "osm",
                    "w": [round(v, 1) for v in world.xy(lon, lat)],
                    "e": ([round(v, 1) for v in europe.xy(lon, lat)]
                          if w <= lon <= e and s <= lat <= n else None),
                })
                farm["units"].append(row["unit_id"])
    licence = ("Farm locations are derived from OpenStreetMap (© OpenStreetMap contributors, "
               "ODbL)")
    if any(f["located_by"] == "repd" for f in farms.values()):
        licence += (" and, where OpenStreetMap has no farm, the Renewable Energy Planning Database "
                    "(contains public sector information licensed under the Open Government "
                    "Licence v3.0)")
    return {
        "licence": licence + ". Links between units and farms are unreviewed proposals.",
        "farms": sorted(farms.values(), key=lambda f: f["name"] or ""),
    }


def write_map(out: Path) -> None:
    (out / "map.json").write_text(json.dumps(build_map(), separators=(",", ":")), encoding="utf-8")
    (out / "farms.json").write_text(json.dumps(build_farms(), ensure_ascii=False,
                                               separators=(",", ":")), encoding="utf-8")
