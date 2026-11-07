"""Snippets are checked live by `wgs check snippets`; these tests only check their shape."""

import ast
import re

import pytest

from wgs.catalogue import load_catalogue
from wgs.checks.snippets import markers, snippet_paths

PATHS = snippet_paths()
IDS = {e["id"]: e for e in load_catalogue()[0]}
SCRIPT = re.compile(r"\A# /// script\n(# .*\n)+# ///\n")


def test_there_are_snippets():
    assert PATHS


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_snippet_is_well_formed(path):
    text = path.read_text(encoding="utf-8")
    assert path.stem in IDS, "file name must be a catalogue entry id"
    assert SCRIPT.match(text), "must start with a PEP 723 script block"
    tree = ast.parse(text)
    assert ast.get_docstring(tree), "needs a docstring saying what it fetches"
    names = {t.id for node in ast.walk(tree) if isinstance(node, ast.Assign)
             for t in node.targets if isinstance(t, ast.Name)}
    assert "df" in names, "must end with a DataFrame called df"
    assert len(text.splitlines()) <= 90, "keep snippets short"
    assert not re.search(r"User-Agent['\"]\s*:\s*['\"]Mozilla", text), "no spoofed user agents"
    mark = markers(text)
    assert set(mark) <= {"needs", "skip"}
    if IDS[path.stem]["access"]["key_required"]:
        assert "needs" in mark, "a keyed source must name its environment variable"


def test_markers_are_read():
    assert markers("x\n# wgs: needs ENTSOE_KEY\n# wgs: skip 2 GB\n") == {
        "needs": "ENTSOE_KEY", "skip": "2 GB"}
