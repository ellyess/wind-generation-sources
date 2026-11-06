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
