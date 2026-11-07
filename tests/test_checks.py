"""Offline checks of the link and cross-check logic. Nothing here touches the network."""

import json

from wgs.catalogue import ROOT, load_catalogue
from wgs.checks.agreement import band, build_agreement
from wgs.checks.links import ERROR_ROLE, _judge, entry_links
from wgs.checks.totals import ADAPTERS, STEP_OF, _step


def test_bands_follow_the_scorecard_audit():
    assert band(1.0) == band(0.85) == band(1.15) == "agrees"
    assert band(0.79) == band(1.3) == "noted"
    assert band(0.69) == band(1.31) == "outside"


def test_agreement_uses_eurostat_first_and_skips_lone_values():
    totals = {"year": 2024, "steps": [], "failures": [], "totals": [
        {"source": "world-ember-monthly", "country": "FR", "twh": 45.9},
        {"source": "eu-eurostat-nrg-bal-peh", "country": "FR", "twh": 47.5},
        {"source": "fr-rte-eco2mix-national", "country": "FR", "twh": 46.8},
        {"source": "world-ember-monthly", "country": "GB", "twh": 83.0},
        {"source": "gb-elexon-bmrs-fuel-type", "country": "GB", "twh": 65.6},
        {"source": "world-ember-monthly", "country": "CL", "twh": 8.0},
        {"source": "eu-eurostat-nrg-bal-peh", "country": "SK", "twh": 0.005},
        {"source": "world-ember-monthly", "country": "SK", "twh": 0.003},
    ]}
    out = build_agreement(totals)["countries"]
    assert out["FR"]["reference"] == "eu-eurostat-nrg-bal-peh"
    fr = {v["source"]: v for v in out["FR"]["values"]}
    assert "ratio" not in fr["eu-eurostat-nrg-bal-peh"]
    assert fr["fr-rte-eco2mix-national"]["band"] == "agrees"
    gb = {v["source"]: v for v in out["GB"]["values"]}
    assert out["GB"]["reference"] == "world-ember-monthly"
    assert gb["gb-elexon-bmrs-fuel-type"]["band"] == "noted"
    assert "CL" not in out  # one source alone has nothing to agree with
    sk = {v["source"]: v for v in out["SK"]["values"]}
    assert sk["world-ember-monthly"]["band"] == "small"


def test_observed_step_from_interval_counts():
    assert _step(2024, 17568) == 30.0  # 366 days of half-hours
    assert _step(2023, 8760) == 60.0
    assert _step(2024, 35136, series=2) == 30.0


def test_every_adapter_names_a_real_entry_with_a_known_step():
    entries, _ = load_catalogue()
    by_id = {e["id"]: e for e in entries}
    for entry_id in ADAPTERS:
        assert entry_id in by_id, entry_id
        assert by_id[entry_id]["resolution"] in STEP_OF or by_id[entry_id]["resolution"] in (
            "daily", "monthly", "annual")


def test_expected_error_evidence_is_judged_the_other_way_round():
    ok = {"state": "ok", "code": 200}
    gone = {"state": "broken", "code": 404}
    assert _judge(ERROR_ROLE, ok)["state"] == "recheck"
    assert _judge(ERROR_ROLE, gone)["state"] == "expected"
    assert _judge("access", gone)["state"] == "broken"


def test_entry_links_are_unique_and_flag_error_evidence():
    entries, _ = load_catalogue()
    miso = next(e for e in entries if e["id"] == "us-miso-wind-generation")
    links = entry_links(miso)
    assert len({u for _, u in links}) == len(links)
    assert any(role == ERROR_ROLE for role, _ in links)


def test_places_cover_every_catalogued_country():
    places = json.loads((ROOT / "geo" / "places.json").read_text())["places"]
    entries, _ = load_catalogue()
    codes = {c for e in entries for c in e["countries"]}
    missing = codes - set(places)
    assert not missing, missing
    assert places["TR"]["continent"] == "Europe"
    assert places["BR"]["continent"] == "Americas"
