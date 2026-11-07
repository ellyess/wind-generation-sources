"""Write the data files the web app reads, and the machine-readable exports."""

from __future__ import annotations

import csv
import datetime as dt
import json
import shutil
from pathlib import Path

from wgs.catalogue import ROOT
from wgs.mapdata import write_map

DATA_OUT = ROOT / "web" / "public" / "data"
CHECKS_DIR = ROOT / "checks"
PLACES = ROOT / "geo" / "places.json"
SNIPPETS = ROOT / "snippets"
CSV_FIELDS = [
    "id", "name", "publisher", "countries", "level", "technology", "measure", "resolution",
    "coverage_start", "coverage_end", "capacity", "coordinates", "curtailment", "timezone",
    "timestamp", "unit", "value", "access_method",
    "url", "key_required", "licence", "spdx", "redistribution", "licence_verified", "traps",
    "status", "reviewed", "last_checked",
]


def _row(entry: dict) -> dict:
    lic, acc, cov = entry["licence"], entry["access"], entry["coverage"]
    conv = entry.get("conventions", {})
    return {
        **{k: conv.get(k, "") for k in ("timezone", "timestamp", "unit", "value")},
        "id": entry["id"],
        "name": entry["name"],
        "publisher": entry["publisher"],
        "countries": " ".join(entry["countries"]),
        "level": entry["level"],
        "technology": entry["technology"],
        "measure": entry["measure"],
        "resolution": entry["resolution"],
        "coverage_start": cov["start"],
        "coverage_end": cov.get("end", ""),
        "capacity": entry["capacity"],
        "coordinates": entry["coordinates"],
        "curtailment": entry.get("curtailment", "unknown"),
        "access_method": acc["method"],
        "url": acc["url"],
        "key_required": acc["key_required"],
        "licence": lic["name"],
        "spdx": lic.get("spdx", ""),
        "redistribution": lic["redistribution"],
        "licence_verified": lic["verified"],
        "traps": len(entry.get("traps", [])),
        "status": entry["status"],
        "reviewed": entry.get("reviewed", True),
        "last_checked": entry["last_checked"],
    }


def load_checks(checks_dir: Path = CHECKS_DIR) -> dict:
    """The latest link check and annual cross-check, trimmed to what the page shows."""
    out: dict = {}
    links = checks_dir / "links.json"
    if links.exists():
        data = json.loads(links.read_text(encoding="utf-8"))
        out["links"] = {"checked": data["checked"], "summary": data["summary"],
                        "entries": data["entries"]}
    snippets = checks_dir / "snippets.json"
    if snippets.exists():
        out["snippets"] = json.loads(snippets.read_text(encoding="utf-8"))["entries"]
    years = sorted(checks_dir.glob("agreement-*.json"))
    if years:
        out["agreement"] = json.loads(years[-1].read_text(encoding="utf-8"))
    return out


def build_site(entries: list[dict], out: Path = DATA_OUT, today: dt.date | None = None) -> None:
    """Write catalogue.json and .csv, checks.json and the map files into the app's data folder."""
    today = today or dt.date.today()
    out.mkdir(parents=True, exist_ok=True)

    entries = sorted(entries, key=lambda e: (e["countries"][0], e["id"]))
    entries = [{**e, "snippet": True} if (SNIPPETS / f"{e['id']}.py").exists() else e
               for e in entries]
    shutil.rmtree(out / "snippets", ignore_errors=True)
    (out / "snippets").mkdir()
    for e in entries:
        if e.get("snippet"):
            shutil.copyfile(SNIPPETS / f"{e['id']}.py", out / "snippets" / f"{e['id']}.py")
    codes = sorted({c for e in entries for c in e["countries"]})
    places = json.loads(PLACES.read_text(encoding="utf-8"))["places"]
    payload = {
        "generated": today.isoformat(),
        "count": len(entries),
        "countries": codes,
        "places": {c: places.get(c, {"name": c, "continent": "Elsewhere"}) for c in codes},
        "sources": entries,
    }
    (out / "catalogue.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out / "catalogue.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(_row(e) for e in entries)
    write_map(out)
    (out / "checks.json").write_text(
        json.dumps(load_checks(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
