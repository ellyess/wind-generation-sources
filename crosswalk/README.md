# Unit-to-farm crosswalk (prototype)

Three scripts feed the map's farm points:
- `build.py` matches unit codes to farms by name, for markets that publish no locations (below).
- `registers.py` reads locations the publisher gives itself, so nothing is guessed: the Danish
  Energy Agency's turbine register (turbines in its 2002 to 2020 production workbook, reprojected
  from UTM 32N) and EIA-860 plant locations for operable US wind plants, whose output EIA-923
  publishes under the same plant code. Run it with
  `uv run --with openpyxl --with pandas --with pyproj python crosswalk/registers.py`.
  On 6 November 2026 it wrote 8,974 Danish turbines and 1,371 US plants.
- `lists.py` places the unit lists in `units/` (one per catalogue entry, format in
  `units/README.md`). Rows with the publisher's own coordinates keep them; the rest are matched
  by name and capacity to OpenStreetMap wind farms in the row's country, by the rules below.
  Run it with `uv run python crosswalk/lists.py`; `output/lists.json` counts each entry's results.
- `corrections.csv` holds checked fixes to single matches (`move` to another farm, or `keep` with
  the reason a flagged match stands). `lists.py` applies them last, and each row's note says who
  checked it.
  In Great Britain, a row that gives a postcode and finds no confident farm falls back to the
  postcode's centroid from Ordnance Survey Code-Point Open (keyless download from the OS Downloads
  API, cached as `.cache/codepo_gb.zip`; Open Government Licence v3.0). Such rows get status
  `approximate`, method `postcode` and `location_source` `os-codepoint-open`: the point is the
  postcode's centroid, not the turbine. A `review` row whose OSM farm lies within 5 km of the
  centroid (about the 90th percentile for onshore links already proposed) and whose capacity does
  not disagree becomes `proposed` by method `name+postcode`; a farther or capacity-contradicted
  candidate gives way to the centroid. Proposed links are never moved. Offshore stations are
  skipped (their postcode is an onshore office), and Northern Ireland (BT) postcodes are not in
  Code-Point Open. Reuse must keep: "Contains OS data © Crown copyright and database right 2026.
  Contains Royal Mail data © Royal Mail copyright and database right 2026. Contains National
  Statistics data © Crown copyright and database right 2026."


Some markets publish wind output per unit with no location:
- AEMO dispatch units (DUIDs) in Australia's National Electricity Market;
- Elexon balancing mechanism units (BMUs) in Great Britain;
- IESO generators in Ontario.

This prototype proposes a link from each unit to a wind farm in OpenStreetMap (OSM). Each link carries the farm's coordinates, its mapped capacity, its OSM link, and any Renewable Energy Planning Database (REPD) or Wikidata IDs. In Great Britain, units that Wikidata links to a farm by their unit code are placed there first; units that OSM cannot place are matched against the REPD itself. The `location_source` column says which of OSM, Wikidata or REPD gave the coordinates.

**Nothing here is verified.** Every row is a proposal for a person to check. The `status` column says how strong the evidence is.

## Run it

```sh
uv run --with openpyxl python crosswalk/build.py            # fetch anything missing, then match
uv run --with openpyxl python crosswalk/build.py --refresh  # fetch everything again
```

Inputs are cached in `crosswalk/.cache/`, which is not committed. Results go to `crosswalk/output/`, one CSV per market, plus `summary.json`.

| Input | From |
|---|---|
| AEMO wind units, station names, registered capacity | NEM Registration and Exemption List, sheet "PU and Scheduled Loads" |
| Elexon wind units, lead party, generation capacity | Elexon Insights API, `/reference/bmunits/all` |
| IESO wind generators | IESO Generator Output and Capability report (current day) |
| Station name and REPD id behind each Elexon unit | [OSUKED Power Station Dictionary](https://github.com/OSUKED/Power-Station-Dictionary) (MIT), pinned to its last data commit (4 May 2024) |
| Wind farms | OSM via Overpass: `power=plant` + `plant:source=wind`, inside the country or province. GB also searches a box around its waters for offshore farms, farms with mixed sources (`wind;solar`) and farms tagged `construction:power=plant`. Battery and solar sites are dropped |
| GB unit-to-farm links | [Wikidata](https://www.wikidata.org/) (CC0) via its keyless SPARQL endpoint: every item with property [P11610](https://www.wikidata.org/wiki/Property:P11610) "National Grid Balancing Mechanism unit ID", with its coordinates (P625), nameplate capacity (P2109), OSM relation (P402), REPD id (P9891) and type (P31). 422 items carrying 658 unit codes on 7 November 2026; the answer is cached as `.cache/wikidata/bmu_items.json` |
| GB wind sites, second pass | [Renewable Energy Planning Database](https://www.gov.uk/government/publications/renewable-energy-planning-database-monthly-extract) (DESNZ), Q2 2026 extract. Wind sites that are operational, under construction or awaiting construction (1,273). British National Grid coordinates are converted to WGS84 in the script |

## How a link is proposed

1. **Shared planning-database ID.** For Elexon units, the Power Station Dictionary gives the station's Renewable Energy Planning Database (REPD) ID. Where an OSM farm carries the same `repd:id`, the link is a direct join, not a guess.
2. **Names.** Names are compared after dropping words that only say "wind farm" (wind, farm, energy, limited and so on).
3. **Distinctive words.** A match must share a distinctive word. Place words shared by many farms (creek, hill, range, north) count for nothing on their own. Differing stage numbers ("Crookwell 2" against "Crookwell 3") are penalised.
4. **Unit codes.** The dictionary's station name is tried first. For Elexon units whose lead party is a trader or a large utility, the unit code is tried as a name prefix (`GRIFW-1` → "Griffin").
5. **Capacity.** Units that point at the same farm are added together, and their total is compared with the farm's mapped capacity.
6. **REPD second pass (GB only).** Units still at `review` or `unmatched` are matched again, against REPD sites instead of OSM farms, by the same rules: a shared REPD ID first, then names and capacity. The REPD row replaces the OSM row only when its status is better, or when both are `review` and the REPD site's capacity is closer. OSM links are kept wherever they hold.
7. **ID check.** Where a link rests on a shared REPD ID, REPD's own name for that ID must share a distinctive word with the unit's names. If it does not, the link drops to `review`. This catches dictionary errors: the dictionary lists Hornsea 1's REPD ID among East Anglia One's, which had joined East Anglia One to Hornsea 1 with full confidence.
8. **Wikidata's unit links (GB only, applied last).** Wikidata gives some power stations their balancing mechanism unit codes (P11610, the National Grid code such as `WHILW-1`). The code is an exact key, so it outranks a name match, a code prefix and a REPD row: method `wikidata-bmu`. The point is, in order, the OSM farm the item links to (P402), an OSM farm tagged with the item, the existing OSM candidate when it is the same farm, and otherwise the item's own coordinates (`location_source` `wikidata`). The row is `proposed` when the item is a wind farm with one location and the units' summed capacity agrees with one of the item's capacities (or the OSM farm's, within 0.35 to 1.6); otherwise `review`. A Wikidata `review` row never unseats an existing `proposed` link: the link is noted instead. Where the earlier candidate was a different farm (an OSM farm whose own `wikidata` tag names another item, or no shared ID or name), `notes` names it and its distance; where it was the same farm more than 5 km away (a coarse REPD offshore point, say), `notes` says how far the point moved. Supplier units that Wikidata links to one farm are placed too, unless their National Grid code begins `AG-` (a real aggregate).
9. **Status:**
   - **`proposed`:** a strong name match, capacity that does not contradict it, and no close second candidate. Or a code prefix plus capacities that agree within 10%. Or a Wikidata unit link as above.
   - **`review`:** a plausible candidate that needs a look. The `runner_up` and `notes` columns say why.
   - **`unmatched`:** no usable candidate.
   - **`aggregate`:** an Elexon supplier unit that sums many small embedded sites, and that Wikidata does not link to one farm. It has no single farm to match.

Each row also gives `farm_state` (operating or under construction in OSM; the REPD status for REPD rows), and `notes` say when a REPD point is shared by several sites or lies offshore.

## Results (7 November 2026)

| Market | Units | Farms searched | Proposed | Review | Unmatched |
|---|---|---|---|---|---|
| AEMO NEM | 109 | 122 OSM | 80 (61% of registered MW) | 19 | 10 |
| Elexon BM | 287 | 727 OSM, 1,273 REPD, 245 Wikidata links | 229 (87% of MW) | 27 (12%) | 27 (0.1%), plus 4 supplier aggregates (0.4%) |
| IESO | 45 | 102 OSM | 27 | 5 | 13 |

**What the wider OSM query and REPD changed in GB.** Before them, Elexon stood at 149 proposed (48% of MW), 43 under review (17%) and 82 unmatched (34%, about 10.9 GW of 32.2 GW). Unmatched capacity is now 1.6 GW. Of the 163 proposed links, 149 come from OSM and 14 from REPD; 16 of the 65 under review take their location from REPD. AEMO and IESO results are unchanged.

**What Wikidata's unit links changed in GB.** Before them, Elexon stood at 163 proposed (62% of MW), 65 under review (32%), 46 unmatched (5%) and 13 aggregates (2%). Wikidata links 244 of the 286 distinct wind units (by National Grid code; 245 rows, since Elexon lists `T_WLNYO-4` twice) to 157 items. 225 of those rows are now `proposed` and 16 `review`; 3 items have no location and 1 links a true aggregate (`AG-`), so those 4 rows keep their earlier result. Of the 241 rows placed, 28 had no candidate before (Hornsea 2's Sonningmay and Soundmark units, Hywind, Rhyl Flats, Achany, Crystal Rig, and 9 supplier units that turn out to be single farms such as Rothes and Paul's Hill), 176 confirm the earlier farm within 5 km, 20 keep the farm but move off a coarse REPD offshore point (12 to 26 km: Moray East and West, Race Bank, Sofia, Galloper, Walney 1 and 2, Hornsea 2), and 17 replace a different farm. The proposed rows take their point from OSM for 193 units and from Wikidata's own coordinates for 32 (13 farms, mostly offshore farms OSM does not map as plants). AEMO, IESO and the unit lists (`lists.json`) are unchanged.

**Checks so far:**
- **AEMO regions.** All 80 proposed AEMO links, and all 19 under review, fall inside the bounding box of the unit's own NEM region. That is a coarse check, independent of the names.
- **Two routes agree.** Before the dictionary was added, name matching alone had proposed farms for 51 of the units that now join by REPD ID. 48 of the 51 agree. The 3 that disagreed are all Walney: units `WLNYO-3` and `WLNYO-4` joined by REPD ID to OSM's "Walney 1 & 2". REPD itself names that ID "Walney 3", and these units now link to that REPD site, so the ID on the OSM farm looks wrong.
- **Known locations.** A spot check of 11 well-known farms (Macarthur, Hornsdale, Clyde, London Array, Gwynt y Môr, Wolfe Island and others) put every OSM-based link within 5 km of the farm's published location.
- **Wikidata against the name matches.** 17 of the 241 placed units had an earlier candidate that was a different farm, 13 of them more than 5 km away: Dogger Bank A and B (10 units, 63 and 71 km from the Dogger Bank C that names had picked), East Anglia One (2 units, 140 km from Hornsea 1, the dictionary error below) and `T_BROCW-1` (199 km from Brockaghboy in Northern Ireland; Elexon's own unit name is "Broken Cross WF", which is Wikidata's farm). The other 4 are neighbours within 5 km: Sanquhar Community and Sanquhar II swapped (3 units) and `T_WISTW-2` on Windy Standard II rather than the unbuilt Windy Standard III. Where the units carry their own evidence, it sides with Wikidata: Elexon's unit name for Broken Cross, the lead party for East Anglia One, and capacity for Dogger Bank A and B (5 units summing to 1,200 MW each, Wikidata's figure) and for Sanquhar Community (32 MW against 31 MW).
- **Wikidata is community-edited**, so its links are evidence, not verification. Spot checks on 7 November 2026: the point chosen for each of the 115 onshore Wikidata items that give a REPD id (P9891) lies a median 1.1 km from that REPD site, and 102 within 5 km. The far ones are mostly REPD's error, not Wikidata's: Hill of Towie's OSM point is 0.6 km from the publisher's own turbine mean (`units/gb-hill-of-towie-scada.csv`) but 21 km from REPD's; Causeymire's Wikidata point is 1.3 km from OSM's farm and 20 km from REPD's. One is Wikidata's: Dalquhandy carries REPD id 4189, whose REPD site is 77 km away, while REPD's "Douglas West and Dalquhandy" (5393) is 2 km from the OSM farm Wikidata links. Wikidata also treats Walney 1 to 4 as one item, so Walney Extension's units share Walney's point. Of Wikidata's own coordinates, Beinn an Tuirc and Solwaybank lie within 1.5 km of both OSM and REPD.
- **REPD offshore points are coarse.** Against Wikidata's coordinates, REPD placed Greater Gabbard 4 km away, but Hornsea 2 18 km, Moray West 19 km, Race Bank 22 km and Moray East 23 km away. Its own point for East Anglia 1 is 59 km from the farm. Several offshore sites share one point (East Anglia 1, 3 and 4; Hornsea 1, 3 and 4; Sofia and Dogger Bank C). Treat a `location_source` of `repd` offshore as a region, not a site. Onshore REPD points are site points.

## Known gaps

- **The Elexon gap is nearly closed; 12% of GB capacity still needs a person.** Wikidata's unit links settled Dogger Bank A and B, Hornsea 2, East Anglia One and Walney 1 and 2. Of the 27 `review` rows left, 16 are Wikidata links whose Elexon capacity disagrees with the farm's, though the farm itself is not in doubt:
  - **Seagreen** (6 units, 1,773 MW against 1,075 MW), **South Kyle** (one unit at 427 MW against 240 MW), **Galloper** (one unit reports 386 MW, so four units sum to nearly twice the farm), **Thanet** (518 MW against 300 MW), **Farr** (two units at 92 MW each against 92 MW) and **Kilgallioch Extension** (225 MW against 62 MW).
  - **Strathy North** stays at review, and **Aikengall** (`AKGLW-1`) and **Greengairs East** stay unmatched: Wikidata links them but gives no location.
  - The other 10 are small onshore code-prefix or name matches that Wikidata does not cover (Boulfruich, Boyndie, Novar, Wether Hill and others).

  A short, hand-checked override file, or a capacity rule that trusts the farm's figure over Elexon's, would settle the first group.
- **Farms missing from OSM as plants.** Newer farms, or farms mapped only as individual turbines, have no plant to match. In AEMO these include Uungula, MacIntyre, Wambo, Clarke Creek and Ryan Corner. In IESO they include Dillon and Railbed. Grouping OSM turbines into farms would recover some of them.
- **IESO capacity.** The IESO report gives each generator's hourly capability for one day, not its installed capacity. The prototype treats the day's highest figure as a floor, which can only rule a farm out.
- **Timing.** OSM shows today's map. Farms that were repowered or decommissioned need OSM's history to match older output.

## Licence

The CSVs in `output/` are derived from OpenStreetMap. They are © OpenStreetMap contributors and available under the [Open Database License](https://opendatacommons.org/licenses/odbl/). That is a share-alike licence, so anything built from these files must stay under the ODbL. Keep them separate from the catalogue entries, which are CC BY 4.0.

Unit-to-farm links in `elexon-bm.csv` with method `wikidata-bmu`, and the coordinates of rows whose `location_source` is `wikidata`, come from [Wikidata](https://www.wikidata.org/), whose structured data are released under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). No attribution is required; the credit "Unit-to-farm links and some coordinates from Wikidata (CC0)" is given as a courtesy. CC0 data can sit inside an ODbL file without conditions.

Rows in `elexon-bm.csv` whose `location_source` is `repd` take their farm name, capacity, status and coordinates from the Renewable Energy Planning Database, published by the Department for Energy Security and Net Zero under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Any reuse must keep this attribution: "Contains public sector information licensed under the Open Government Licence v3.0." The OGL allows this information to sit inside an ODbL file, as long as the attribution travels with it. The unit lists come from AEMO, Elexon and IESO under the terms recorded in their catalogue entries. The Power Station Dictionary is MIT-licensed. The code is MIT.
