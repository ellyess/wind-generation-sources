# Unit lists

One CSV per catalogue entry, named `<entry-id>.csv`, listing the wind units or plants whose
output that entry publishes. `crosswalk/lists.py` places each row on the map: it keeps the
publisher's own coordinates where given, and otherwise matches the name to an OpenStreetMap
wind farm in `area`.

Columns:

| Column | Meaning |
|---|---|
| `entry` | the catalogue entry id (same as the file name) |
| `unit_id` | the code or name exactly as it appears in the publisher's output data |
| `unit_name` | a clean human name for matching (drop codes, "UEE", "EOL", "parque eólico" and the like only if they are noise) |
| `alt_names` | other names separated by `;` (owner's name, older name, English name) |
| `capacity_mw` | installed capacity as the publisher states it; blank if not published |
| `area` | ISO 3166-1 alpha-2 code of the country (or ISO 3166-2, e.g. `CA-AB`, for a province) |
| `lat`, `lon` | only when the publisher itself publishes the location (WGS84 decimal degrees) |
| `location_source` | `publisher` when lat/lon come from the publisher; blank otherwise |
| `source_url` | the file or page the list was read from |
| `notes` | anything a reviewer needs (e.g. "hybrid wind-solar plant") |

Never type coordinates from memory or from a third-party site: leave lat/lon blank and let the
matcher look the name up.

## Per-list notes

- **de-netztransparenz-eeg-movement-data:** one row per wind installation that appears in the
  four transmission operators' EEG movement-data files (Amprion's is 2024, the others 2025).
  `unit_id` is the EEG installation key. Coordinates and capacity (gross, Bruttoleistung) come
  from the Bundesnetzagentur Marktstammdatenregister bulk export of 6 November 2026
  (EinheitenWind.xml, Data licence Germany, attribution, version 2.0).
