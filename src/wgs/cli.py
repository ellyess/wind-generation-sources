"""Command line: `wgs validate`, `wgs build` and `wgs check`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wgs.catalogue import ROOT, load_catalogue

CHECKS_DIR = ROOT / "checks"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wgs", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check every entry against the schema and house rules")
    build = sub.add_parser("build", help="write the web app's data files and the CSV/JSON exports")
    build.add_argument("--out", type=Path, default=ROOT / "web" / "public" / "data")
    check = sub.add_parser("check", help="check the live sources (needs network)")
    check.add_argument("what", choices=["links", "totals", "snippets"])
    check.add_argument("--year", type=int, default=2024,
                       help="calendar year for the totals cross-check (default 2024)")
    check.add_argument("--only", help="comma-separated entry ids (totals and snippets)")
    check.add_argument("--out", type=Path, default=CHECKS_DIR)
    args = parser.parse_args(argv)

    entries, problems = load_catalogue()
    for problem in problems:
        print(problem, file=sys.stderr)
    fatal = [p for p in problems if p.fatal]

    if args.command == "validate":
        print(f"{len(entries)} entries valid, {len(fatal)} errors, "
              f"{len(problems) - len(fatal)} warnings")
        return 1 if fatal else 0

    if args.command == "check":
        return _check(args, entries)

    if fatal:
        print("refusing to build with errors", file=sys.stderr)
        return 1
    from wgs.site import build_site

    build_site(entries, args.out)
    print(f"built {len(entries)} entries into {args.out}")
    return 0


def _check(args: argparse.Namespace, entries: list[dict]) -> int:
    if args.what == "links":
        from wgs.checks.links import check_links

        report = check_links(entries)
        _write(args.out / "links.json", report)
        s = report["summary"]
        print(f"{s['ok']} links ok, {s['broken']} broken, {s['recheck']} traps to recheck, "
              f"{s['unchecked']} could not be checked")
        for entry_id, row in report["entries"].items():
            for kind in ("broken", "recheck"):
                for link in row[kind]:
                    print(f"{kind}: {entry_id}: {link['role']}: {link['url']}", file=sys.stderr)
        return 1 if s["broken"] else 0

    if args.what == "snippets":
        from wgs.checks.snippets import check_snippets

        path = args.out / "snippets.json"
        previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        only = set(args.only.split(",")) if args.only else None
        report = check_snippets(only, previous)
        _write(path, report)
        s = report["summary"]
        print(f"{s['ok']} snippets ran, {s['failed']} failed, {s['skipped']} skipped")
        for entry_id, row in report["entries"].items():
            if row["result"] == "failed" and (not only or entry_id in only):
                print(f"failed: {entry_id}: {row['error']}", file=sys.stderr)
        return 1 if s["failed"] else 0

    from wgs.checks.agreement import build_agreement
    from wgs.checks.totals import run_totals

    only = set(args.only.split(",")) if args.only else None
    totals = run_totals(entries, args.year, only)
    report = build_agreement(totals)
    _write(args.out / f"agreement-{args.year}.json", report)
    for iso, row in report["countries"].items():
        cells = ", ".join(f"{v['source']} {v['twh']}" + (f" ({v['ratio']})" if "ratio" in v
                                                          else "") for v in row["values"])
        print(f"{iso}: {cells}")
    for fail in report["failures"]:
        print(f"failed: {fail['source']}: {fail['error']}", file=sys.stderr)
    bad_steps = [s for s in report["steps"] if not s["agrees"]]
    for s in bad_steps:
        print(f"time step: {s['source']} states {s['stated_minutes']} min, data show "
              f"{s['observed_minutes']} min", file=sys.stderr)
    return 1 if bad_steps else 0


if __name__ == "__main__":
    raise SystemExit(main())
