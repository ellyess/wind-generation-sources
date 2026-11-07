"""Checks on the map files the build writes."""

import json

from wgs.catalogue import load_catalogue
from wgs.mapdata import GEO, MARKET_ENTRY, build_farms


def test_outlines_are_lon_lat_and_coded():
    data = json.loads((GEO / "countries.geojson").read_text())
    codes = {f["properties"]["iso"] for f in data["features"]}
    assert {"AU", "NZ", "US", "BR", "GB", "MT", "CY"} <= codes
    for f in data["features"][:20]:
        ring = f["geometry"]["coordinates"][0]
        ring = ring[0] if f["geometry"]["type"] == "MultiPolygon" else ring
        assert all(-180 <= x <= 180 and -90 <= y <= 90 for x, y in ring)


def test_farms_point_at_real_entries_and_carry_the_odbl_notice():
    entries, _ = load_catalogue()
    ids = {e["id"] for e in entries}
    assert set(MARKET_ENTRY.values()) <= ids
    out = build_farms()
    assert "ODbL" in out["licence"]
    for farm in out["farms"]:
        assert farm["entry"] in ids
        assert farm["n"] >= 1
        assert farm["name"] and not farm["name"].startswith("(")
        assert -90 <= farm["lat"] <= 90 and "w" not in farm
        assert farm["located_by"] in {"osm", "repd", "ens", "eia-860", "publisher"}


def test_register_points_fall_inside_their_country():
    boxes = {"dk-ens-turbine-register": (54.4, 57.9, 7.5, 15.3),
             "us-eia-923-plant-generation": (18.0, 72.0, -180.0, -64.0)}
    for farm in build_farms()["farms"]:
        if farm["entry"] in boxes:
            s, n, w, e = boxes[farm["entry"]]
            assert s <= farm["lat"] <= n and w <= farm["lon"] <= e, farm
