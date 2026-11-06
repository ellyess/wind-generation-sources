"""Checks on the map projections and the map and farm files the site build writes."""

import math
import re

import pytest

from wgs.catalogue import load_catalogue
from wgs.mapdata import (
    EU_LAT0,
    EU_LON0,
    MARKET_ENTRY,
    build_farms,
    build_map,
    equal_earth,
    laea,
)


def test_equal_earth_known_values():
    assert equal_earth(0, 0) == (0, 0)
    # Half-width of the unit-sphere Equal Earth map at the equator.
    assert equal_earth(180, 0)[0] == pytest.approx(2.70663, abs=1e-4)
    x, y = equal_earth(-120, 45)
    assert (x, y) == pytest.approx((-equal_earth(120, 45)[0], -equal_earth(120, -45)[1]))


def test_laea_is_centred_and_preserves_distance_from_centre():
    assert laea(EU_LON0, EU_LAT0) == pytest.approx((0, 0))
    # A point 10 degrees north of the centre lies 2 sin(5 degrees) away on the unit sphere.
    assert laea(EU_LON0, EU_LAT0 + 10) == pytest.approx((0, 2 * math.sin(math.radians(5))))


def _numbers(d: str):
    vals = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
    return vals[0::2], vals[1::2]


def test_world_view_contains_the_whole_projection():
    m = build_map()
    _, _, w, h = (float(v) for v in m["world"]["viewBox"].split())
    xs, ys = _numbers(m["world"]["frame"])
    assert min(xs) >= -0.1 and max(xs) <= w + 0.1
    assert min(ys) >= -0.1 and max(ys) <= h + 0.1
    assert {c["iso"] for c in m["world"]["countries"]} >= {"AU", "NZ", "US", "BR", "GB"}


def test_europe_detail_has_the_catalogue_countries_drawn():
    m = build_map()
    drawn = {c["iso"] for c in m["europe"]["countries"]}
    assert {"GB", "DE", "MT", "IS", "CY"} <= drawn


def test_farms_point_at_real_entries_and_carry_the_odbl_notice():
    entries, _ = load_catalogue()
    ids = {e["id"] for e in entries}
    assert set(MARKET_ENTRY.values()) <= ids
    out = build_farms()
    assert "ODbL" in out["licence"]
    for farm in out["farms"]:
        assert farm["entry"] in ids
        assert farm["units"]
        assert farm["name"] and not farm["name"].startswith("(")
