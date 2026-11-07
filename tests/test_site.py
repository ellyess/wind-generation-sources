import csv
import json

from wgs.catalogue import load_catalogue
from wgs.site import build_site


def test_build_writes_the_data_files_and_exports(tmp_path):
    entries, _ = load_catalogue()
    out = tmp_path / "data"
    build_site(entries, out)
    for name in ("checks.json", "countries.geojson", "farms.json"):
        assert (out / name).exists(), name
    data = json.loads((out / "catalogue.json").read_text())
    assert data["count"] == len(entries) == len(data["sources"])
    with (out / "catalogue.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(entries)
    assert {r["id"] for r in rows} == {e["id"] for e in entries}
