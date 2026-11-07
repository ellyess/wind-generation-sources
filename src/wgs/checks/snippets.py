"""Run every snippet in `snippets/` and record whether it ran cleanly."""

from __future__ import annotations

import datetime as dt
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from wgs.catalogue import ROOT

SNIPPETS = ROOT / "snippets"
TIMEOUT = 300  # seconds per snippet
MARKER = re.compile(r"^# wgs: (needs|skip)\s+(.+)$", re.M)


def markers(text: str) -> dict[str, str]:
    """The `# wgs: needs ENV` and `# wgs: skip reason` lines of a snippet."""
    return {kind: value.strip() for kind, value in MARKER.findall(text)}


def snippet_paths(snippets: Path = SNIPPETS) -> list[Path]:
    return sorted(snippets.glob("*.py"))


def run_one(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    mark = markers(text)
    if "skip" in mark:
        return {"result": "skipped", "reason": mark["skip"]}
    if "needs" in mark and not os.environ.get(mark["needs"]):
        return {"result": "skipped", "reason": f"needs {mark['needs']}"}
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is needed to run the snippets")
    start = time.monotonic()
    try:
        proc = subprocess.run([uv, "run", "-q", "--script", str(path)], capture_output=True,
                              text=True, timeout=TIMEOUT, cwd=path.parent)
    except subprocess.TimeoutExpired:
        return {"result": "failed", "error": f"timed out after {TIMEOUT} s"}
    seconds = round(time.monotonic() - start, 1)
    out = [line for line in proc.stdout.splitlines() if line.strip()]
    if proc.returncode or not out:
        err = [line for line in proc.stderr.splitlines() if line.strip()]
        return {"result": "failed", "seconds": seconds,
                "error": (err[-1] if err else "printed nothing")[:300]}
    return {"result": "ok", "seconds": seconds, "summary": out[-1][:200]}


def check_snippets(only: set[str] | None = None, previous: dict | None = None) -> dict:
    today = dt.date.today().isoformat()
    entries = dict((previous or {}).get("entries", {}))
    for path in snippet_paths():
        if only and path.stem not in only:
            continue
        row = run_one(path)
        row["checked"] = today
        old = entries.get(path.stem, {})
        row["last_ok"] = today if row["result"] == "ok" else old.get("last_ok")
        entries[path.stem] = {k: v for k, v in row.items() if v is not None}
    entries = {k: v for k, v in sorted(entries.items()) if (SNIPPETS / f"{k}.py").exists()}
    counts = {r: sum(1 for e in entries.values() if e["result"] == r)
              for r in ("ok", "failed", "skipped")}
    return {"checked": today, "summary": counts, "entries": entries}
