"""A small HTTP client for the checks: standard library only, polite, with retries."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = (
    "wind-generation-sources-checks/0.1 "
    "(+https://github.com/ellyess/wind-generation-sources)"
)
MAX_WAIT = 90  # seconds; a longer Retry-After counts as a failure


class FetchError(RuntimeError):
    pass


def get(url: str, *, timeout: float = 90, retries: int = 3,
        headers: dict[str, str] | None = None) -> bytes:
    """GET a URL and return the body. Retries server errors and short rate limits."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            wait = _retry_after(exc)
            if exc.code == 429 and wait is not None and wait <= MAX_WAIT:
                time.sleep(wait + 1)
                continue
            if exc.code >= 500 and attempt < retries - 1:
                time.sleep(2 ** attempt * 3)
                continue
            raise FetchError(f"HTTP {exc.code} from {url}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 3)
                continue
            raise FetchError(f"{exc} from {url}") from exc
    raise FetchError(f"gave up on {url}")


def get_json(url: str, **kwargs: Any) -> Any:
    return json.loads(get(url, **kwargs))


def _retry_after(exc: urllib.error.HTTPError) -> float | None:
    value = exc.headers.get("Retry-After") if exc.headers else None
    if value and value.isdigit():
        return float(value)
    try:  # Energinet puts the wait in the body instead
        body = exc.read().decode("utf-8", "replace")
    except Exception:
        return None
    for word in body.replace(".", " ").split():
        if word.isdigit():
            return float(word)
    return None
