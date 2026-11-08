"""Locations that publishers give themselves, for the map's farm layer.

Unlike `build.py`, nothing here is matched or guessed: the publisher's own register gives each
unit's position, and the unit code joins it to the output file.

- Denmark: the Danish Energy Agency's turbine register (ETRS89 / UTM 32N coordinates), kept to
  turbines that appear in its monthly production workbook (2002 to 2020).
- United States: EIA-860 plant locations, kept to plants with an operable wind generator. EIA-923
  publishes their monthly net generation under the same plant code.

    uv run --with openpyxl --with pandas --with pyproj python crosswalk/registers.py
    uv run --with openpyxl --with pandas --with pyproj python crosswalk/registers.py --refresh

Writes `output/ens-dk.csv` and `output/eia-860.csv` in the same columns as the matched markets,
with status `published`.
"""

from __future__ import annotations

import argparse
import csv
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
OUT = HERE / "output"
UA = "wind-generation-sources-crosswalk/0.1 (+https://github.com/ellyess/wind-generation-sources)"

EIA_YEAR = 2025
SOURCES = {
    # The register's media id changes with each monthly refresh; this is the snapshot fetched.
    "ens_anlaeg.xlsx": "https://ens.dk/media/4945/download",
    "ens_maanedsdata.xlsx": "https://ens.dk/media/4948/download",
    f"eia860_{EIA_YEAR}.zip": f"https://www.eia.gov/electricity/data/eia860/xls/eia860{EIA_YEAR}.zip",
}
COLUMNS = ["market", "unit_id", "unit_name", "unit_capacity_mw", "status", "location_source",
           "farm_name", "lat", "lon", "notes"]


def fetch(refresh: bool) -> None:
    CACHE.mkdir(exist_ok=True)
    for name, url in SOURCES.items():
        path = CACHE / name
        if path.exists() and not refresh:
            continue
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            path.write_bytes(r.read())


def denmark() -> list[dict]:
    produced: set[str] = set()
    book = pd.ExcelFile(CACHE / "ens_maanedsdata.xlsx")
    for sheet in book.sheet_names:
        ids = pd.read_excel(book, sheet_name=sheet, header=None, skiprows=9, usecols=[0])[0]
        produced |= {str(v).strip() for v in ids.dropna()}
    reg = pd.ExcelFile(CACHE / "ens_anlaeg.xlsx")
    to_wgs = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)
    rows = []
    for sheet in reg.sheet_names:
        df = pd.read_excel(reg, sheet_name=sheet, header=9)
        df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
        gsrn = df.columns[0]
        cap = next(c for c in df.columns if c.startswith("Capacity"))
        x = next(c for c in df.columns if c.startswith("X (east)"))
        y = next(c for c in df.columns if c.startswith("Y (north)"))
        maker = next(c for c in df.columns if c.startswith("Manufact"))
        place = next(c for c in df.columns if c.startswith("Local authority") and "no" not in c)
        df = df.dropna(subset=[gsrn, x, y])
        df = df[df[gsrn].astype(str).str.strip().isin(produced)]
        lon, lat = to_wgs.transform(df[x].astype(float).to_numpy(), df[y].astype(float).to_numpy())
        for (_, r), lo, la in zip(df.iterrows(), lon, lat, strict=True):
            kw = r[cap]
            name = " ".join(str(v) for v in (r[maker], f"{kw:g} kW" if pd.notna(kw) else "")
                            if str(v) not in ("", "nan"))
            rows.append({
                "market": "ens-dk", "unit_id": str(r[gsrn]).strip(),
                "unit_name": f"{name} turbine, {r[place]}" if name else f"Turbine, {r[place]}",
                "unit_capacity_mw": round(kw / 1000, 3) if pd.notna(kw) else "",
                "status": "published", "location_source": "ens", "farm_name": "",
                "lat": round(la, 5), "lon": round(lo, 5),
                "notes": "decommissioned" if "fmeldte" in sheet and "Ikke" not in sheet else "",
            })
    return rows


def united_states() -> list[dict]:
    z = zipfile.ZipFile(CACHE / f"eia860_{EIA_YEAR}.zip")
    wind = pd.read_excel(z.open(f"3_2_Wind_Y{EIA_YEAR}.xlsx"), sheet_name="Operable", header=1)
    wind = wind.dropna(subset=["Plant Code"])
    cap = wind.groupby("Plant Code")["Nameplate Capacity (MW)"].sum()
    plants = pd.read_excel(z.open(f"2___Plant_Y{EIA_YEAR}.xlsx"), header=1)
    plants = plants[plants["Plant Code"].isin(cap.index)].dropna(subset=["Latitude", "Longitude"])
    return [{
        "market": "eia-860", "unit_id": str(int(r["Plant Code"])), "unit_name": r["Plant Name"],
        "unit_capacity_mw": round(float(cap[r["Plant Code"]]), 1), "status": "published",
        "location_source": "eia-860", "farm_name": r["Plant Name"],
        "lat": round(float(r["Latitude"]), 5), "lon": round(float(r["Longitude"]), 5),
        "notes": r["State"],
    } for _, r in plants.iterrows()]


def write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(exist_ok=True)
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["unit_id"]))
    print(f"{name}: {len(rows)} units")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true", help="fetch every input again")
    args = ap.parse_args()
    fetch(args.refresh)
    write("ens-dk.csv", denmark())
    write("eia-860.csv", united_states())


if __name__ == "__main__":
    main()
