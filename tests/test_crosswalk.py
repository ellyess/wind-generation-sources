"""Checks on the crosswalk prototype's name and capacity parsing."""

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "crosswalk_build", Path(__file__).resolve().parents[1] / "crosswalk" / "build.py")
cw = importlib.util.module_from_spec(spec)
sys.modules["crosswalk_build"] = cw
spec.loader.exec_module(cw)


def test_same_farm_scores_high():
    assert cw.name_score("Macarthur Wind Farm", "MacArthur Wind Farm") > 0.95
    assert cw.name_score("Hornsea 1 Limited", "Hornsea Project One") > 0.9


def test_shared_place_word_alone_is_not_a_match():
    # "Creek" is in many farm names; it proves nothing on its own.
    assert cw.name_score("Clarke Creek Wind Farm", "Flyers Creek Wind Farm") <= 0.5
    # Similar spelling with no word in common.
    assert cw.name_score("Hawkesdale Wind Farm", "Hornsdale Windfarm") <= 0.5


def test_different_stage_numbers_are_penalised():
    assert cw.name_score("Crookwell 2 Wind Farm", "Crookwell 3 Wind Farm") < cw.name_score(
        "Crookwell 2 Wind Farm", "Crookwell 2 Wind Farm")


def test_capacity_parsing():
    assert cw.parse_mw("322.2 MW") == 322.2
    assert cw.parse_mw("2.3 GW") == 2300
    assert cw.parse_mw("2000 kW") == 2
    assert cw.parse_mw("48") == 48
    assert cw.parse_mw("yes") is None


def test_bmu_stem():
    assert cw.bmu_stem("GRIFW-1") == "grif"
    assert cw.bmu_stem("ABRBO-1") == "abrb"


def test_shared_repd_id_is_proposed_unless_capacity_contradicts():
    assert cw.classify(1.0, "repd-id", 1.02, 1.0, floor=False) == "proposed"
    assert cw.classify(1.0, "repd-id", 3.0, 1.0, floor=False) == "review"


def test_bng_to_wgs84_matches_pyproj_onshore():
    # Reference values from pyproj (EPSG:27700 to EPSG:4326). Offshore, pyproj uses the OSTN15
    # grid and differs by up to about 130 m, so the check uses onshore points.
    for (e, n), (lat, lon) in {
        (530268, 179640): (51.500694, -0.124628),  # Westminster
        (325000, 673000): (55.944167, -3.202386),  # Edinburgh
        (140000, 40000): (50.202774, -5.644916),  # Cornwall
    }.items():
        got = cw.bng_to_wgs84(e, n)
        assert abs(got[0] - lat) < 1e-4 and abs(got[1] - lon) < 1e-4


REPD_CSV = (
    "Ref ID,Old Ref ID,Site Name,Technology Type,Development Status (short),"
    "Installed Capacity (MWelec),X-coordinate,Y-coordinate\n"
    "100,B0001,Glen Example Wind Farm,Wind Onshore,Operational,50,325000,673000\n"
    "101,,Sunny Fields,Solar Photovoltaics,Operational,20,325000,673000\n"
    "102,,Old Moor Wind Farm,Wind Onshore,Abandoned,30,325000,673000\n"
)


def test_repd_keeps_live_wind_sites_and_joins_on_old_id(tmp_path):
    path = tmp_path / "repd.csv"
    path.write_bytes(REPD_CSV.encode("cp1252"))
    repd = cw.load_repd(path)
    assert [p.name for p in repd] == ["Glen Example Wind Farm"]
    assert repd[0].tags["repd:id"] == "100;B0001"

    # The unit's name says nothing; the dictionary's old REPD id carries the join.
    unit = cw.Unit("elexon-bm", "T_GLNX-1", ["Something Else Ltd"], 49.0, "generation",
                   {"repd": {"B0001"}})
    (row,) = cw.match_market([unit], repd)
    assert (row["status"], row["method"], row["location_source"]) == ("proposed", "repd-id", "repd")
    assert row["osm_url"] == ""
    assert abs(row["lat"] - 55.944) < 1e-3


def test_dictionary_id_naming_another_farm_is_demoted():
    hornsea = cw.Plant("repd", "2525", ["Hornsea 1 - Heron & Njord"], 1218.0, 53.7, 1.4,
                       {"repd:id": "2525;B0263", "status": "Operational"})
    unit = cw.Unit("elexon-bm", "T_EAAO-1", ["East Anglia One Limited"], 358.0, "generation",
                   {"repd": {"2525", "2470"}})
    row = {"unit_id": "T_EAAO-1", "status": "proposed", "method": "repd-id",
           "repd_id": "2525", "notes": ""}
    cw.check_repd_names([unit], [row], [hornsea])
    assert row["status"] == "review"
    assert "Hornsea 1" in row["notes"]


def test_words_joined_on_one_side_are_joined_on_the_other():
    assert cw.join_compounds(["doggerbank", "1"], ["dogger", "bank", "a"]) == ["doggerbank", "a"]
    assert cw.name_score("Doggerbank OWF Project 1", "Dogger Bank") > 0.85


_lspec = importlib.util.spec_from_file_location(
    "crosswalk_lists", Path(__file__).resolve().parents[1] / "crosswalk" / "lists.py")
cl = importlib.util.module_from_spec(_lspec)
_lspec.loader.exec_module(cl)


def test_postcode_is_read_from_column_or_notes():
    assert cl.unit_postcode({"postcode": "ne24 1se"}) == "NE241SE"
    assert cl.unit_postcode({"notes": "Onshore wind; station postcode KW17  2PJ (from the "
                                      "register's station address)"}) == "KW172PJ"
    assert cl.unit_postcode({"notes": "Onshore wind; England"}) == ""


def test_postcode_fallback_fills_gaps_and_keeps_osm_links():
    # Postcode centroid near Edinburgh (Code-Point Open style: quality, lat, lon).
    codepoint = {"EH11AA": (10, 55.95, -3.19)}
    units = {u: {"unit_id": u, "area": "GB", "postcode": "EH1 1AA", "notes": "Onshore wind",
                 "unit_name": u} for u in ("near", "far", "none", "kept", "sea")}
    units["sea"]["notes"] = "Offshore wind"
    units["ni"] = {"unit_id": "ni", "area": "GB", "postcode": "BT75 0LN", "notes": ""}
    osm = {"farm_name": "Glen Farm", "osm_url": "https://www.openstreetmap.org/way/1",
           "farm_capacity_mw": 10.0, "unit_capacity_mw": 9.0, "farm_capacity_ratio": 0.9}
    rows = [
        {"unit_id": "near", "status": "review", "method": "name", "lat": 55.96, "lon": -3.19,
         "notes": "", **osm},
        {"unit_id": "far", "status": "review", "method": "name", "lat": 57.5, "lon": -4.2,
         "notes": "", **osm},
        {"unit_id": "none", "status": "unmatched", "method": "name", "lat": 52.0, "lon": 0.1,
         "notes": "", "unit_name": "Small Turbine; Owner Ltd", **osm},
        {"unit_id": "kept", "status": "proposed", "method": "name", "lat": 58.9, "lon": -3.1,
         "notes": "", **osm},
        {"unit_id": "sea", "status": "unmatched", "lat": "", "lon": "", "notes": ""},
        {"unit_id": "ni", "status": "unmatched", "lat": "", "lon": "", "notes": ""},
    ]
    cl.postcode_fallback(rows, units, codepoint)
    near, far, none, kept, sea, ni = rows
    # An OSM candidate close to the postcode, with agreeing capacity, is confirmed.
    assert (near["status"], near["method"], near["lat"]) == ("proposed", "name+postcode", 55.96)
    # A distant OSM candidate gives way to the postcode centroid, marked as approximate.
    assert (far["status"], far["method"], far["location_source"]) == (
        "approximate", "postcode", "os-codepoint-open")
    assert (far["lat"], far["lon"], far["osm_url"]) == (55.95, -3.19, "")
    assert "not at the turbine" in far["notes"] and "Glen Farm (review)" in far["notes"]
    assert none["status"] == "approximate" and none["farm_name"] == "Small Turbine"
    # Proposed OSM links keep their place; a distant postcode only adds a note.
    assert (kept["status"], kept["lat"]) == ("proposed", 58.9)
    assert "check: station postcode" in kept["notes"]
    # Offshore stations and Northern Ireland postcodes stay unplaced.
    assert sea["status"] == ni["status"] == "unmatched"
    why = cl.unplaced_postcodes(rows, units, codepoint)
    assert why["offshore (postcode is onshore)"] == 1
    assert why["Northern Ireland postcode (not in Code-Point Open)"] == 1


def _wd_item(qid, label, bmus, points=(), caps=(), rels=(), types=("onshore wind farm",)):
    return cw.WikidataItem(qid, label, set(bmus), list(points), list(caps), set(rels), set(),
                           set(types))


def _elexon(code, cap):
    return cw.Unit("elexon-bm", f"T_{code}", ["Some Party Ltd"], cap, "registered",
                   {"ng_code": code, "repd": set()})


def _row(unit, status, method, farm, lat, lon, url=""):
    return {"market": "elexon-bm", "unit_id": unit.unit_id, "unit_name": unit.names[0],
            "unit_capacity_mw": unit.capacity_mw, "unit_capacity_kind": "registered",
            "status": status, "method": method, "location_source": "osm", "farm_name": farm,
            "lat": lat, "lon": lon, "osm_url": url, "repd_id": "", "wikidata": "", "notes": ""}


def test_wikidata_bmu_link_beats_a_name_match_and_names_the_dropped_candidate():
    right = cw.Plant("relation", 7, ["Broken Cross Wind Farm"], 50.0, 55.6, -3.8, {})
    wrong = cw.Plant("relation", 8, ["Brockaghboy Wind Farm"], 47.5, 54.9, -6.7, {})
    unit = _elexon("BROCW-1", 48.0)
    rows = [_row(unit, "review", "code-prefix", wrong.name, wrong.lat, wrong.lon,
                 "https://www.openstreetmap.org/relation/8")]
    items = {"BROCW-1": _wd_item("Q1", "Broken Cross wind farm", ["BROCW-1"],
                                 points=[(55.61, -3.81)], caps=[48.0], rels=[7])}
    outcome = cw.apply_wikidata([unit], rows, items, [right, wrong])
    (row,) = rows
    # The OSM farm the item links to (P402) gives the point; the name match is dropped.
    assert (row["status"], row["method"], row["location_source"]) == (
        "proposed", "wikidata-bmu", "osm")
    assert (row["lat"], row["osm_url"], row["wikidata"]) == (
        55.6, "https://www.openstreetmap.org/relation/7", "Q1")
    assert "dropped the earlier candidate Brockaghboy Wind Farm" in row["notes"]
    assert outcome["different farm, > 5 km"] == 1


def test_wikidata_point_used_when_no_osm_farm_and_proposed_link_stands_against_doubt():
    placed, doubted = _elexon("HYWDW-1", 30.0), _elexon("THNTO-1", 600.0)
    rows = [_row(placed, "unmatched", "", "", "", ""),
            _row(doubted, "proposed", "name", "Thanet Wind Farm", 51.43, 1.63)]
    items = {"HYWDW-1": _wd_item("Q2", "Hywind Scotland", ["HYWDW-1"], points=[(57.48, -1.35)],
                                 caps=[30.0], types=["floating wind farm"]),
             "THNTO-1": _wd_item("Q3", "Thanet Wind Farm", ["THNTO-1"], points=[(51.43, 1.63)],
                                 caps=[300.0], types=["offshore wind farm"])}
    outcome = cw.apply_wikidata([placed, doubted], rows, items, [])
    hywind, thanet = rows
    # No OSM farm: the item's own coordinates (P625), labelled as Wikidata's.
    assert (hywind["status"], hywind["location_source"], hywind["lat"]) == (
        "proposed", "wikidata", 57.48)
    # Twice the item's capacity makes the Wikidata row `review`, which does not unseat a
    # proposed link: the row is kept and the Wikidata link is noted.
    assert (thanet["status"], thanet["method"]) == ("proposed", "name")
    assert "capacity disagrees" in thanet["notes"] and "Q3" in thanet["notes"]
    assert outcome["newly placed"] == 1
