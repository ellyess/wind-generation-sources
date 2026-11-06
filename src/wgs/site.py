"""Write the static site and the machine-readable exports."""

from __future__ import annotations

import csv
import datetime as dt
import json
import shutil
from pathlib import Path

from wgs.catalogue import ROOT
from wgs.mapdata import write_map

SITE_SRC = ROOT / "site"
CSV_FIELDS = [
    "id", "name", "publisher", "countries", "level", "technology", "measure", "resolution",
    "coverage_start", "coverage_end", "capacity", "coordinates", "curtailment", "access_method",
    "url", "key_required", "licence", "spdx", "redistribution", "licence_verified", "traps",
    "status", "last_checked",
]


def _row(entry: dict) -> dict:
    lic, acc, cov = entry["licence"], entry["access"], entry["coverage"]
    return {
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
        "last_checked": entry["last_checked"],
    }


def build_site(entries: list[dict], out: Path, today: dt.date | None = None) -> None:
    """Copy the static page and write catalogue.json and catalogue.csv beside it."""
    today = today or dt.date.today()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for path in SITE_SRC.iterdir():
        if path.name == "dist":
            continue
        target = out / path.name
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)

    entries = sorted(entries, key=lambda e: (e["countries"][0], e["id"]))
    payload = {
        "generated": today.isoformat(),
        "count": len(entries),
        "countries": sorted({c for e in entries for c in e["countries"]}),
        "sources": entries,
    }
    (out / "catalogue.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out / "catalogue.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(_row(e) for e in entries)
    write_map(out)
