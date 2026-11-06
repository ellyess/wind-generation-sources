"""Command line: `wgs validate` and `wgs build`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wgs.catalogue import ROOT, load_catalogue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wgs", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check every entry against the schema and house rules")
    build = sub.add_parser("build", help="write the site and the CSV/JSON exports")
    build.add_argument("--out", type=Path, default=ROOT / "site" / "dist")
    args = parser.parse_args(argv)

    entries, problems = load_catalogue()
    for problem in problems:
        print(problem, file=sys.stderr)
    fatal = [p for p in problems if p.fatal]

    if args.command == "validate":
        print(f"{len(entries)} entries valid, {len(fatal)} errors, "
              f"{len(problems) - len(fatal)} warnings")
        return 1 if fatal else 0

    if fatal:
        print("refusing to build with errors", file=sys.stderr)
        return 1
    from wgs.site import build_site

    build_site(entries, args.out)
    print(f"built {len(entries)} entries into {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
