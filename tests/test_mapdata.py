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
        assert farm["located_by"] in {"osm", "repd", "ens", "eia-860", "publisher",
                                      "os-codepoint-open", "wikidata"}


def test_register_points_fall_inside_their_country():
    boxes = {"dk-ens-turbine-register": (54.4, 57.9, 7.5, 15.3),
             "us-eia-923-plant-generation": (18.0, 72.0, -180.0, -64.0)}
    for farm in build_farms()["farms"]:
        if farm["entry"] in boxes:
            s, n, w, e = boxes[farm["entry"]]
            assert s <= farm["lat"] <= n and w <= farm["lon"] <= e, farm


def test_postcode_points_carry_the_os_credit():
    out = build_farms()
    if any(f["located_by"] == "os-codepoint-open" for f in out["farms"]):
        assert "Contains OS data © Crown copyright and database right" in out["licence"]
        assert "postcode's centroid, not at the turbine" in out["licence"]


def test_capacity_is_positive_mw_where_known():
    farms = build_farms()["farms"]
    sized = [f for f in farms if "mw" in f]
    assert len(sized) > len(farms) / 2
    for f in sized:
        assert isinstance(f["mw"], float) and 0 < f["mw"] < 5000, f
    # A point from a turbine register is a turbine (or a few sharing a coordinate).
    assert all(f["mw"] / f["n"] <= 20 for f in sized
               if f.get("turbine") and f["located_by"] in {"publisher", "ens"})
    sofia = [f for f in sized if f["name"].startswith("Sofia")]
    assert all(f["mw"] <= 1400 for f in sofia)  # capped at the farm, not 4 BM units x 457 MW


def test_multi_country_entries_name_the_country_of_each_point():
    for farm in build_farms()["farms"]:
        if farm["entry"] == "ie-semo-daily-meter-data":
            assert farm["iso"] in {"IE", "GB"}
            if farm["iso"] == "GB":
                assert farm["lat"] > 54 and farm["lon"] > -8.2, farm
        elif farm["entry"] == "us-eia-923-plant-generation":
            assert "iso" not in farm
