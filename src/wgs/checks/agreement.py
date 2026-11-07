"""Compare each country's annual wind total across the sources that report it.

The reference is Eurostat's gross electricity production where Eurostat covers the country,
and Ember otherwise. The bands follow the PyVWF scorecard audit: a ratio within 0.85-1.15 of
the reference agrees, 0.70-1.30 is noted, and anything further out is flagged. Gross
production runs above what transmission operators meter, so ratios a little under 1 are
normal; the entry's traps usually say why. Fleets under 0.05 TWh a year are compared but not
judged, because rounding alone moves their ratio. Ember and Eurostat compile national
figures, so an exact match can mean the same upstream data rather than independent
confirmation; the check catches a series that measures only part of a fleet, not a shared error.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

REFERENCES = ("eu-eurostat-nrg-bal-peh", "world-ember-monthly")
BANDS = ((0.85, 1.15, "agrees"), (0.70, 1.30, "noted"))
SMALL_TWH = 0.05


def band(ratio: float) -> str:
    for lo, hi, name in BANDS:
        if lo <= ratio <= hi:
            return name
    return "outside"


def build_agreement(totals: dict, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    by_country: dict[str, list[dict]] = defaultdict(list)
    for t in totals["totals"]:
        by_country[t["country"]].append(t)

    countries = {}
    for iso, rows in sorted(by_country.items()):
        refs = {r["source"]: r for r in rows if r["source"] in REFERENCES}
        ref_id = next((s for s in REFERENCES if s in refs), None)
        if ref_id is None or len(rows) < 2:
            continue  # nothing to compare against
        ref = refs[ref_id]["twh"]
        values = []
        for r in sorted(rows, key=lambda r: (r["source"] in REFERENCES, r["source"])):
            row = {"source": r["source"], "twh": r["twh"]}
            if r["source"] != ref_id and ref > 0:
                row["ratio"] = round(r["twh"] / ref, 3)
                row["band"] = "small" if ref < SMALL_TWH else band(row["ratio"])
            values.append(row)
        countries[iso] = {"reference": ref_id, "values": values}
    return {
        "checked": today.isoformat(),
        "year": totals["year"],
        "method": __doc__.strip().replace("\n", " "),
        "bands": [{"low": lo, "high": hi, "name": n} for lo, hi, n in BANDS],
        "countries": countries,
        "steps": totals["steps"],
        "failures": totals["failures"],
    }
