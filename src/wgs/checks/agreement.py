"""Compare each country's annual wind total across the sources that report it.

The reference is the national figure where one exists for the whole wind fleet over the calendar
year: a national source read live, or a figure taken from the national publisher's own report,
quoted and linked. A series that covers only part of the fleet, such as Great Britain's
transmission-metered wind, or a fiscal year, is compared but never used as the reference. Where
there is no such national figure, the reference is Eurostat's gross electricity production, and
outside Eurostat's countries Ember. A national figure is only as good as its publisher: it can be
preliminary, and it can draw the country's borders differently from the international compilers.
The bands follow the PyVWF scorecard audit: a ratio within 0.85-1.15 of the reference agrees,
0.70-1.30 is noted, and anything further out is flagged. Gross production runs above what
transmission operators meter, so ratios a little under 1 are normal; the entry's traps usually say
why. Fleets under 0.05 TWh a year are compared but not judged, because rounding alone moves their
ratio. Ember and Eurostat compile national figures, so an exact match can mean the same upstream
data rather than independent confirmation; the check catches a series that measures only part of a
fleet, not a shared error.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from pathlib import Path

import yaml

from wgs.catalogue import ROOT

CHECKS_DIR = ROOT / "checks"
EUROSTAT, EMBER = "eu-eurostat-nrg-bal-peh", "world-ember-monthly"
BANDS = ((0.85, 1.15, "agrees"), (0.70, 1.30, "noted"))
SMALL_TWH = 0.05

# Every national adapter in totals.py, and whether its total can be the country's reference:
# (eligible, short publisher name, reason). Decided from the entry's own notes and traps.
NATIONAL_ADAPTERS: dict[str, tuple[bool, str, str]] = {
    "es-ree-redata": (True, "REE", "Spain as a whole, all systems, from the national "
                      "generation structure; excludes only estimated self-consumption."),
    "fr-rte-eco2mix-national": (True, "RTE", "The entry calls it the complete French national "
                                "series, offshore included."),
    "dk-energinet-production-settlement": (True, "Energinet", "Settled production from the "
                                           "national meter data hub, all four wind size "
                                           "classes, both price areas."),
    "de-smard": (False, "SMARD", "ENTSO-E Transparency figures; the entry does not establish "
                 "that they cover the whole fleet."),
    "gb-elexon-bmrs-fuel-type": (False, "Elexon", "Transmission-connected wind only; wind on "
                                 "the distribution network is outside FUELHH."),
    "be-elia-wind-production": (False, "Elia", "Measured and upscaled estimate over Elia's "
                                "monitored capacity, not a reported total."),
    "nz-ea-emi-generation-md": (False, "Electricity Authority", "Grid-connected generators "
                                "only: about 28 MW on the distribution network is outside, and "
                                "Mahinerangi is metered as hydro."),
}


def band(ratio: float) -> str:
    for lo, hi, name in BANDS:
        if lo <= ratio <= hi:
            return name
    return "outside"


def load_figures(year: int, checks_dir: Path = CHECKS_DIR) -> list[dict]:
    """Curated national figures for the year, or none if the file does not exist."""
    path = checks_dir / f"national-figures-{year}.yaml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8"))["figures"]


def _figure_key(fig: dict) -> str:
    return fig.get("entry") or f"national-{fig['country']}"


def _reference(iso: str, rows: list[dict], figures: dict[str, dict]) -> dict | None:
    """Pick the reference: whole-fleet national adapter, curated figure, Eurostat, Ember."""
    sources = {r["source"] for r in rows}
    for entry_id, (ok, name, why) in NATIONAL_ADAPTERS.items():
        if ok and entry_id in sources:
            return {"source": entry_id, "kind": "national-adapter", "name": name, "why": why}
    fig = figures.get(iso)
    if fig and fig["whole_fleet"]:
        return {"source": _figure_key(fig), "kind": "national-figure", "name": fig["short"],
                "publisher": fig["publisher"], "url": fig["url"],
                "why": " ".join(fig["why"].split())}
    if EUROSTAT in sources:
        return {"source": EUROSTAT, "kind": "eurostat", "name": "Eurostat",
                "why": "No whole-fleet calendar-year national figure; Eurostat covers the country."}
    if EMBER in sources:
        return {"source": EMBER, "kind": "ember", "name": "Ember",
                "why": "No whole-fleet calendar-year national figure, and outside Eurostat."}
    return None


def build_agreement(totals: dict, today: dt.date | None = None,
                    figures: list[dict] | None = None) -> dict:
    today = today or dt.date.today()
    if figures is None:
        figures = load_figures(totals["year"])
    by_country: dict[str, list[dict]] = defaultdict(list)
    for t in totals["totals"]:
        by_country[t["country"]].append(t)
    curated = {f["country"]: f for f in figures}
    for iso, fig in curated.items():
        if not any(r["source"] == _figure_key(fig) for r in by_country[iso]):
            by_country[iso].append({"source": _figure_key(fig), "country": iso,
                                    "twh": fig["twh"], "figure": fig})

    countries = {}
    for iso, rows in sorted(by_country.items()):
        reference = _reference(iso, rows, curated)
        if reference is None or len(rows) < 2:
            continue  # nothing to compare against
        ref_id = reference["source"]
        ref = next(r["twh"] for r in rows if r["source"] == ref_id)
        values = []
        for r in sorted(rows, key=lambda r: (r["source"] == ref_id, r["source"])):
            row = {"source": r["source"], "twh": r["twh"]}
            if "figure" in r:
                row.update(national=True, publisher=r["figure"]["short"], url=r["figure"]["url"])
            if r["source"] != ref_id and ref > 0:
                row["ratio"] = round(r["twh"] / ref, 3)
                row["band"] = "small" if ref < SMALL_TWH else band(row["ratio"])
            values.append(row)
        countries[iso] = {"reference": reference, "values": values}
    return {
        "checked": today.isoformat(),
        "year": totals["year"],
        "method": " ".join(__doc__.split()),
        "bands": [{"low": lo, "high": hi, "name": n} for lo, hi, n in BANDS],
        "national_adapters": {k: {"eligible": ok, "why": why}
                              for k, (ok, _, why) in NATIONAL_ADAPTERS.items()},
        "countries": countries,
        "steps": totals["steps"],
        "failures": totals["failures"],
    }


def totals_from_report(report: dict) -> dict:
    """Rebuild the totals input from a saved report, so the reference rule can be re-applied
    without fetching every source again. Countries the saved report skipped are not recovered."""
    rows = [{"source": v["source"], "country": iso, "twh": v["twh"]}
            for iso, c in report["countries"].items() for v in c["values"]
            if not v.get("national")]
    return {"year": report["year"], "totals": rows, "steps": report["steps"],
            "failures": report["failures"]}
