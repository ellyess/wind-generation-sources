"""Load and check catalogue entries."""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schema" / "source.schema.json"
SOURCES_DIR = ROOT / "sources"
STALE_AFTER_DAYS = 365


@dataclass
class Problem:
    path: Path
    message: str
    fatal: bool = True

    def __str__(self) -> str:
        kind = "error" if self.fatal else "warning"
        return f"{kind}: {self.path.name}: {self.message}"


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class _Loader(yaml.SafeLoader):
    """SafeLoader with YAML 1.2 booleans, and dates kept as strings.

    YAML 1.1 reads NO (Norway), ON and Y as booleans. Here only true and false are, so
    country codes never need quoting. Dates stay strings so they validate against the
    schema's "date" format.
    """


_Loader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)
_Loader.add_constructor(
    "tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node)
)


def parse_entry(text: str) -> dict:
    data = yaml.load(text, Loader=_Loader)  # a SafeLoader subclass
    if not isinstance(data, dict):
        raise ValueError("entry is not a mapping")
    return data


def _load_yaml(path: Path) -> dict:
    return parse_entry(path.read_text(encoding="utf-8"))


def check_entry(path: Path, entry: dict, validator: Draft202012Validator,
                today: dt.date | None = None) -> list[Problem]:
    """Return every problem with one entry, schema and house rules alike."""
    today = today or dt.date.today()
    problems = [
        Problem(path, f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}")
        for e in sorted(validator.iter_errors(entry), key=lambda e: list(e.absolute_path))
    ]
    if problems:
        return problems

    if entry["id"] != path.stem:
        problems.append(Problem(path, f"id '{entry['id']}' does not match file name"))

    cov = entry["coverage"]
    if "end" in cov and cov["end"] < cov["start"]:
        problems.append(Problem(path, "coverage end is before start"))
    if entry["status"] in ("discontinued", "fixed-release") and "end" not in cov:
        problems.append(Problem(path, f"a {entry['status']} source needs a coverage end"))
    if entry["status"] == "active" and "end" not in cov and not cov.get("update"):
        problems.append(Problem(
            path, "an active, open-ended source should say how often it updates (coverage.update)",
            fatal=False))

    lic = entry["licence"]
    if lic["verified"] and "url" not in lic:
        problems.append(Problem(path, "licence marked verified but has no url"))
    if lic["redistribution"] in {"allowed", "allowed-with-attribution"} and not lic["verified"]:
        problems.append(Problem(
            path, "redistribution is only stated as allowed once the licence is verified"))

    by = entry.get("checked_by", "").lower()
    says_unreviewed = "not yet reviewed" in by or by.startswith("automated research")
    if says_unreviewed and entry.get("reviewed") is not False:
        problems.append(Problem(path, "checked_by says not yet reviewed, so set reviewed: false"))
    if entry.get("reviewed") is True:
        problems.append(Problem(path, "omit reviewed once a person has checked the entry"))

    checked = dt.date.fromisoformat(entry["last_checked"])
    if checked > today:
        problems.append(Problem(path, "last_checked is in the future"))
    elif (today - checked).days > STALE_AFTER_DAYS:
        problems.append(Problem(path, f"not checked for over {STALE_AFTER_DAYS} days",
                                fatal=False))
    if (latest := _latest_dated_change(entry)) and latest > checked:
        problems.append(Problem(
            path, f"a correction or trap is dated {latest}, after last_checked ({checked})",
            fatal=False))
    return problems


_DATED_CHANGE = re.compile(r"\bCorrected (\d{4}-\d{2}-\d{2})")


def _texts(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [t for v in value.values() for t in _texts(v)]
    if isinstance(value, list):
        return [t for v in value for t in _texts(v)]
    return []


def _latest_dated_change(entry: dict) -> dt.date | None:
    """The latest "Corrected YYYY-MM-DD" in the entry's text, or trap `found` date."""
    dates = [m for t in _texts(entry) for m in _DATED_CHANGE.findall(t)]
    dates += [str(t["found"]) for t in entry.get("traps", []) if t.get("found")]
    parsed = []
    for d in dates:
        try:
            parsed.append(dt.date.fromisoformat(d))
        except ValueError:
            continue
    return max(parsed, default=None)


def load_catalogue(sources_dir: Path = SOURCES_DIR,
                   today: dt.date | None = None) -> tuple[list[dict], list[Problem]]:
    """Load every entry. Entries with fatal problems are left out of the result."""
    validator = Draft202012Validator(load_schema(), format_checker=FormatChecker())
    entries, problems = [], []
    for path in sorted(sources_dir.glob("*.yaml")):
        try:
            entry = _load_yaml(path)
        except (yaml.YAMLError, ValueError) as exc:
            problems.append(Problem(path, f"cannot read: {exc}"))
            continue
        found = check_entry(path, entry, validator, today)
        problems.extend(found)
        if not any(p.fatal for p in found):
            entries.append(entry)
    seen: dict[str, Path] = {}
    for entry in entries:
        if entry["id"] in seen:
            problems.append(Problem(seen[entry["id"]], f"duplicate id {entry['id']}"))
        seen[entry["id"]] = Path(entry["id"])
    return entries, problems
