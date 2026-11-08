"""Offline checks of the link and cross-check logic. Nothing here touches the network."""

import json

from wgs.catalogue import ROOT, load_catalogue
from wgs.checks import links
from wgs.checks.agreement import (
    NATIONAL_ADAPTERS,
    band,
    build_agreement,
    load_figures,
    totals_from_report,
)
from wgs.checks.links import ERROR_ROLE, _judge, check_url, entry_links, is_file_link
from wgs.checks.totals import ADAPTERS, STEP_OF, _step


def test_bands_follow_the_scorecard_audit():
    assert band(1.0) == band(0.85) == band(1.15) == "agrees"
    assert band(0.79) == band(1.3) == "noted"
    assert band(0.69) == band(1.31) == "outside"


FIGURE = {"country": "LK", "publisher": "Ceylon Electricity Board (CEB)", "short": "CEB",
          "twh": 0.792, "url": "https://ceb.lk/x.pdf", "whole_fleet": True, "why": "All wind."}


def test_agreement_prefers_whole_fleet_national_figures_then_eurostat_then_ember():
    totals = {"year": 2024, "steps": [], "failures": [], "totals": [
        {"source": "world-ember-monthly", "country": "FR", "twh": 45.9},
        {"source": "eu-eurostat-nrg-bal-peh", "country": "FR", "twh": 47.5},
        {"source": "fr-rte-eco2mix-national", "country": "FR", "twh": 46.8},
        {"source": "world-ember-monthly", "country": "GB", "twh": 83.0},
        {"source": "gb-elexon-bmrs-fuel-type", "country": "GB", "twh": 65.6},
        {"source": "world-ember-monthly", "country": "BE", "twh": 13.1},
        {"source": "eu-eurostat-nrg-bal-peh", "country": "BE", "twh": 13.8},
        {"source": "be-elia-wind-production", "country": "BE", "twh": 12.6},
        {"source": "world-ember-monthly", "country": "LK", "twh": 1.324},
        {"source": "world-irena-irenastat", "country": "LK", "twh": 0.797},
        {"source": "world-ember-monthly", "country": "CL", "twh": 8.0},
        {"source": "eu-eurostat-nrg-bal-peh", "country": "SK", "twh": 0.005},
        {"source": "world-ember-monthly", "country": "SK", "twh": 0.003},
    ]}
    out = build_agreement(totals, figures=[FIGURE])["countries"]
    # A whole-fleet national adapter is the reference, and Eurostat gets a ratio like any other.
    assert out["FR"]["reference"]["source"] == "fr-rte-eco2mix-national"
    assert out["FR"]["reference"]["kind"] == "national-adapter"
    fr = {v["source"]: v for v in out["FR"]["values"]}
    assert "ratio" not in fr["fr-rte-eco2mix-national"]
    assert fr["eu-eurostat-nrg-bal-peh"]["band"] == "agrees"
    # A partial national series is compared but never the reference.
    assert out["GB"]["reference"]["source"] == "world-ember-monthly"
    gb = {v["source"]: v for v in out["GB"]["values"]}
    assert gb["gb-elexon-bmrs-fuel-type"]["band"] == "noted"
    assert out["BE"]["reference"]["kind"] == "eurostat"
    # A curated national figure is the reference, named and linked.
    lk = out["LK"]
    assert lk["reference"]["kind"] == "national-figure"
    assert lk["reference"]["name"] == "CEB" and lk["reference"]["url"] == FIGURE["url"]
    lkv = {v["source"]: v for v in lk["values"]}
    assert lkv["national-LK"]["national"] and lkv["national-LK"]["publisher"] == "CEB"
    assert lkv["world-ember-monthly"]["band"] == "outside"
    assert lkv["world-irena-irenastat"]["band"] == "agrees"
    assert "CL" not in out  # one source alone has nothing to agree with
    assert {v["source"]: v for v in out["SK"]["values"]}["world-ember-monthly"]["band"] == "small"


def test_partial_or_fiscal_figures_are_compared_but_not_the_reference():
    totals = {"year": 2024, "steps": [], "failures": [], "totals": [
        {"source": "world-ember-monthly", "country": "LK", "twh": 1.324}]}
    out = build_agreement(totals, figures=[{**FIGURE, "whole_fleet": False}])["countries"]
    assert out["LK"]["reference"]["kind"] == "ember"
    assert {v["source"]: v for v in out["LK"]["values"]}["national-LK"]["ratio"] == 0.598


def test_saved_report_rebuilds_without_the_curated_rows():
    totals = {"year": 2024, "steps": [], "failures": [], "totals": [
        {"source": "world-ember-monthly", "country": "LK", "twh": 1.324},
        {"source": "world-irena-irenastat", "country": "LK", "twh": 0.797}]}
    report = build_agreement(totals, figures=[FIGURE])
    again = totals_from_report(report)
    assert sorted(t["source"] for t in again["totals"]) == sorted(
        t["source"] for t in totals["totals"])
    assert build_agreement(again, figures=[FIGURE])["countries"] == report["countries"]


def test_every_national_adapter_has_an_eligibility_decision():
    national = set(ADAPTERS) - {"eu-eurostat-nrg-bal-peh", "world-ember-monthly",
                                "world-eia-international", "world-irena-irenastat"}
    assert national == set(NATIONAL_ADAPTERS)
    assert not NATIONAL_ADAPTERS["gb-elexon-bmrs-fuel-type"][0]


def test_curated_national_figures_are_complete_and_convert_correctly():
    entries, _ = load_catalogue()
    ids = {e["id"] for e in entries}
    factor = {"GWh": 1e-3, "million kWh": 1e-3, "TWh": 1.0}
    figures = load_figures(2024)
    assert figures
    for f in figures:
        for key in ("country", "publisher", "short", "value", "unit", "twh", "period", "url",
                    "quote", "fetched", "whole_fleet", "why"):
            assert key in f, (f["country"], key)
        assert "calendar 2024" in f["period"]
        assert abs(f["value"] * factor[f["unit"]] - f["twh"]) < 0.0006, f["country"]
        assert f.get("entry") is None or f["entry"] in ids


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


def test_file_link_answered_with_html_is_not_ok(monkeypatch):
    # asep.gob.pa answers any path, real or not, with a 200 HTML page.
    calls = []

    def fake(url, method, timeout):
        calls.append(method)
        return 200, url, "text/html; charset=utf-8"

    monkeypatch.setattr(links, "_request", fake)
    result = check_url("https://example.org/files/ENERO_2013.pdf")
    assert calls == ["HEAD", "GET"]
    assert result["state"] == "unchecked"
    assert _judge(ERROR_ROLE, result)["state"] == "expected"
    assert check_url("https://example.org/report-page")["state"] == "ok"
    assert is_file_link("https://example.org/a/B.XLSX?x=1") and not is_file_link("https://example.org/pdf")
    assert not is_file_link("https://www.dropbox.com/scl/fo/x/a.zip?rlkey=y&dl=0")
    assert not is_file_link("https://gitlab.example.org/g/r/-/blob/master/report.pdf")


def test_unresolved_host_is_asked_again(monkeypatch):
    answers = [{"state": "broken", "code": None, "error": "host not found"},
               {"state": "ok", "code": 200, "final": None}]
    monkeypatch.setattr(links, "_check_url", lambda url, timeout: answers.pop(0))
    monkeypatch.setattr(links, "DNS_RETRY_PAUSE", 0)
    assert check_url("https://example.org/")["state"] == "ok"
