import datetime as dt
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from wgs.catalogue import SOURCES_DIR, check_entry, load_catalogue, load_schema, parse_entry

TODAY = dt.date(2026, 11, 6)
VALIDATOR = Draft202012Validator(load_schema(), format_checker=FormatChecker())

MINIMAL = """\
id: no-example-source
name: Example source
publisher: Example publisher
countries: [NO, ON]
level: farm
technology: onshore
measure: metered-energy
resolution: hourly
coverage:
  start: 2015
capacity: included
coordinates: none
access:
  method: api
  url: https://example.org/
  key_required: false
licence:
  name: Example licence
  redistribution: unclear
  verified: false
status: active
last_checked: 2026-11-01
"""


def check(text: str, name: str = "no-example-source.yaml") -> list[str]:
    return [p.message for p in check_entry(Path(name), parse_entry(text), VALIDATOR, TODAY)]


def test_minimal_entry_is_valid():
    assert check(MINIMAL) == []


def test_norway_is_a_country_code_not_false():
    # YAML 1.1 reads NO and ON as booleans; the loader must not.
    assert parse_entry(MINIMAL)["countries"] == ["NO", "ON"]
    assert parse_entry("a: false\nb: true\n") == {"a": False, "b": True}


def test_dates_stay_strings():
    assert parse_entry(MINIMAL)["last_checked"] == "2026-11-01"


def test_redistribution_cannot_be_allowed_before_the_licence_is_read():
    text = MINIMAL.replace("redistribution: unclear", "redistribution: allowed")
    assert any("verified" in m for m in check(text))


def test_verified_licence_needs_a_url():
    text = MINIMAL.replace("verified: false", "verified: true")
    assert any("no url" in m for m in check(text))


def test_id_must_match_file_name():
    assert any("does not match" in m for m in check(MINIMAL, "other-name.yaml"))


def test_coverage_end_before_start_is_refused():
    text = MINIMAL.replace("  start: 2015\n", "  start: 2015\n  end: 2010\n")
    assert any("before start" in m for m in check(text))


def test_discontinued_needs_an_end():
    text = MINIMAL.replace("status: active", "status: discontinued")
    assert any("coverage end" in m for m in check(text))


def test_future_check_date_is_refused():
    assert any("future" in m for m in check(MINIMAL.replace("2026-11-01", "2027-01-01")))


def test_stale_entry_is_a_warning_not_an_error():
    problems = check_entry(Path("no-example-source.yaml"),
                           parse_entry(MINIMAL.replace("2026-11-01", "2024-01-01")),
                           VALIDATOR, TODAY)
    assert problems and not any(p.fatal for p in problems)


def test_trap_without_evidence_is_refused():
    text = MINIMAL + "traps:\n  - summary: Something goes wrong here.\n"
    assert check(text)


@pytest.mark.parametrize("bad", ["countries: [no]", "countries: [NOR]", "countries: []"])
def test_country_codes_are_two_upper_case_letters(bad):
    assert check(MINIMAL.replace("countries: [NO, ON]", bad))


def test_every_published_entry_is_valid():
    entries, problems = load_catalogue(SOURCES_DIR)
    fatal = [str(p) for p in problems if p.fatal]
    assert fatal == []
    assert len(entries) >= 15
