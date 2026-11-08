"""Check that every link in the catalogue still answers.

A link is "ok" when it returns a 2xx after redirects, "broken" when the server says the page is
gone (404, 410) or the host does not resolve, and "unchecked" when the server refuses automated
clients (401, 403, 429) or times out. Unchecked links are reported, never counted as broken:
several transmission operators block anything that is not a browser.

Some trap evidence is meant to fail (a 404 for a missing year). Those traps carry
`evidence_is_error: true`; an error there is "expected", and a success is reported as
"recheck", because the trap may no longer hold.
"""

from __future__ import annotations

import datetime as dt
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from wgs.checks.http import USER_AGENT

BROKEN_CODES = {404, 410}
REFUSED_CODES = {401, 403, 405, 406, 429, 451}
DNS_RETRY_PAUSE = 5.0
# A link to one of these files that answers with an HTML page has not found the file: some servers
# answer every path, real or not, with a 200 page.
FILE_SUFFIXES = (".pdf", ".xls", ".xlsx", ".xlsb", ".csv", ".zip", ".gz", ".nc", ".parquet", ".7z")


ERROR_ROLE = "trap evidence (an error is expected)"


def entry_links(entry: dict) -> list[tuple[str, str]]:
    """Every (role, url) pair in an entry, in reading order."""
    links = [("access", entry["access"]["url"])]
    if "docs" in entry["access"]:
        links.append(("docs", entry["access"]["docs"]))
    if "url" in entry["licence"]:
        links.append(("licence", entry["licence"]["url"]))
    links += [(ERROR_ROLE if t.get("evidence_is_error") else "trap evidence", t["evidence"])
              for t in entry.get("traps", [])]
    links += [("tool", t["url"]) for t in entry.get("tools", [])]
    seen, out = set(), []
    for role, url in links:
        if url not in seen:
            seen.add(url)
            out.append((role, url))
    return out


def _judge(role: str, result: dict) -> dict:
    if role != ERROR_ROLE:
        return result
    if result["state"] == "ok":
        return {**result, "state": "recheck"}
    return {**result, "state": "expected"}


def is_file_link(url: str) -> bool:
    """A direct link to a file, not a viewer page for one (Dropbox previews, Git /blob/ pages)."""
    parts = urllib.parse.urlsplit(url)
    path = parts.path.lower()
    dropbox_preview = (parts.hostname or "").endswith("dropbox.com") and "dl=1" not in parts.query
    if "/blob/" in path or dropbox_preview:
        return False
    return path.endswith(FILE_SUFFIXES)


def _request(url: str, method: str, timeout: float) -> tuple[int, str, str]:
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": USER_AGENT, "Accept": "*/*", "Range": "bytes=0-2047"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if method == "GET":
            resp.read(2048)
        return resp.status, resp.geturl(), resp.headers.get("Content-Type", "")


def check_url(url: str, timeout: float = 30) -> dict:
    """Return {"state", "code", "final"} for one URL.

    A host that does not resolve is asked once more after a pause before it counts as broken:
    lookups fail now and then when many run at once.
    """
    result = _check_url(url, timeout)
    if result.get("error") == "host not found":
        time.sleep(DNS_RETRY_PAUSE)
        result = _check_url(url, timeout)
    return result


def _check_url(url: str, timeout: float) -> dict:
    code: int | None = None
    for method in ("HEAD", "GET"):
        try:
            status, final, ctype = _request(url, method, timeout)
            if is_file_link(url) and ctype.lower().startswith("text/html"):
                if method == "HEAD":
                    continue
                return {"state": "unchecked", "code": status,
                        "error": "a file link answered with an HTML page"}
            return {"state": "ok", "code": status, "final": final if final != url else None}
        except urllib.error.HTTPError as exc:
            code = exc.code
            if method == "HEAD" and (exc.code in REFUSED_CODES or exc.code in BROKEN_CODES
                                     or exc.code >= 400):
                continue  # many servers mishandle HEAD; ask again with GET
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.gaierror):
                return {"state": "broken", "code": None, "error": "host not found"}
            if method == "HEAD":
                continue
            return {"state": "unchecked", "code": None, "error": str(reason)[:120]}
        except TimeoutError:
            if method == "HEAD":
                continue
            return {"state": "unchecked", "code": None, "error": "timed out"}
        except Exception as exc:  # malformed responses, TLS failures
            if method == "HEAD":
                continue
            return {"state": "unchecked", "code": None, "error": type(exc).__name__}
    if code in BROKEN_CODES:
        return {"state": "broken", "code": code}
    return {"state": "unchecked", "code": code}


def check_links(entries: list[dict], today: dt.date | None = None,
                workers: int = 12) -> dict:
    """Check every distinct URL once and report per entry."""
    today = today or dt.date.today()
    by_entry = {e["id"]: entry_links(e) for e in entries}
    urls = sorted({url for links in by_entry.values() for _, url in links})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(zip(urls, pool.map(check_url, urls), strict=True))
    entries_out = {}
    for entry_id, links in by_entry.items():
        rows = [{"role": role, "url": url, **_judge(role, results[url])}
                for role, url in links]
        entries_out[entry_id] = {
            "ok": sum(r["state"] in ("ok", "expected") for r in rows),
            "broken": [r for r in rows if r["state"] == "broken"],
            "recheck": [r for r in rows if r["state"] == "recheck"],
            "unchecked": [r for r in rows if r["state"] == "unchecked"],
            "total": len(rows),
        }
    states = [r["state"] for row in entries_out.values()
              for r in row["broken"] + row["recheck"] + row["unchecked"]]
    total = sum(row["total"] for row in entries_out.values())
    summary = {s: states.count(s) for s in ("broken", "recheck", "unchecked")}
    summary["ok"] = total - sum(summary.values())
    return {"checked": today.isoformat(), "summary": summary, "entries": entries_out}
