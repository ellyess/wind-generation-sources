# Unit-to-farm crosswalk (prototype)

Some markets publish wind output per unit with no location:
- AEMO dispatch units (DUIDs) in Australia's National Electricity Market;
- Elexon balancing mechanism units (BMUs) in Great Britain;
- IESO generators in Ontario.

This prototype proposes a link from each unit to a wind farm in OpenStreetMap (OSM). Each link carries the farm's coordinates, its mapped capacity, its OSM link, and any Renewable Energy Planning Database (REPD) or Wikidata IDs. In Great Britain, units that OSM cannot place are matched against the REPD itself, and the `location_source` column says which of the two gave the coordinates.

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
| GB wind sites, second pass | [Renewable Energy Planning Database](https://www.gov.uk/government/publications/renewable-energy-planning-database-monthly-extract) (DESNZ), Q2 2026 extract. Wind sites that are operational, under construction or awaiting construction (1,273). British National Grid coordinates are converted to WGS84 in the script |

## How a link is proposed

1. **Shared planning-database ID.** For Elexon units, the Power Station Dictionary gives the station's Renewable Energy Planning Database (REPD) ID. Where an OSM farm carries the same `repd:id`, the link is a direct join, not a guess.
2. **Names.** Names are compared after dropping words that only say "wind farm" (wind, farm, energy, limited and so on).
3. **Distinctive words.** A match must share a distinctive word. Place words shared by many farms (creek, hill, range, north) count for nothing on their own. Differing stage numbers ("Crookwell 2" against "Crookwell 3") are penalised.
4. **Unit codes.** The dictionary's station name is tried first. For Elexon units whose lead party is a trader or a large utility, the unit code is tried as a name prefix (`GRIFW-1` → "Griffin").
5. **Capacity.** Units that point at the same farm are added together, and their total is compared with the farm's mapped capacity.
6. **REPD second pass (GB only).** Units still at `review` or `unmatched` are matched again, against REPD sites instead of OSM farms, by the same rules: a shared REPD ID first, then names and capacity. The REPD row replaces the OSM row only when its status is better, or when both are `review` and the REPD site's capacity is closer. OSM links are kept wherever they hold.
7. **ID check.** Where a link rests on a shared REPD ID, REPD's own name for that ID must share a distinctive word with the unit's names. If it does not, the link drops to `review`. This catches dictionary errors: the dictionary lists Hornsea 1's REPD ID among East Anglia One's, which had joined East Anglia One to Hornsea 1 with full confidence.
8. **Status:**
   - **`proposed`:** a strong name match, capacity that does not contradict it, and no close second candidate. Or a code prefix plus capacities that agree within 10%.
   - **`review`:** a plausible candidate that needs a look. The `runner_up` and `notes` columns say why.
   - **`unmatched`:** no usable candidate.
   - **`aggregate`:** an Elexon supplier unit that sums many small embedded sites. It has no single farm to match.

Each row also gives `farm_state` (operating or under construction in OSM; the REPD status for REPD rows), and `notes` say when a REPD point is shared by several sites or lies offshore.

## Results (6 November 2026)

| Market | Units | Farms searched | Proposed | Review | Unmatched |
|---|---|---|---|---|---|
| AEMO NEM | 109 | 122 OSM | 80 (61% of registered MW) | 19 | 10 |
| Elexon BM | 287 | 727 OSM, 1,273 REPD | 163 (62% of MW) | 65 (32%) | 46 (5%), plus 13 supplier aggregates (2%) |
| IESO | 45 | 102 OSM | 27 | 5 | 13 |

**What the wider OSM query and REPD changed in GB.** Before them, Elexon stood at 149 proposed (48% of MW), 43 under review (17%) and 82 unmatched (34%, about 10.9 GW of 32.2 GW). Unmatched capacity is now 1.6 GW. Of the 163 proposed links, 149 come from OSM and 14 from REPD; 16 of the 65 under review take their location from REPD. AEMO and IESO results are unchanged.

**Checks so far:**
- **AEMO regions.** All 80 proposed AEMO links, and all 19 under review, fall inside the bounding box of the unit's own NEM region. That is a coarse check, independent of the names.
- **Two routes agree.** Before the dictionary was added, name matching alone had proposed farms for 51 of the units that now join by REPD ID. 48 of the 51 agree. The 3 that disagreed are all Walney: units `WLNYO-3` and `WLNYO-4` joined by REPD ID to OSM's "Walney 1 & 2". REPD itself names that ID "Walney 3", and these units now link to that REPD site, so the ID on the OSM farm looks wrong.
- **Known locations.** A spot check of 11 well-known farms (Macarthur, Hornsdale, Clyde, London Array, Gwynt y Môr, Wolfe Island and others) put every OSM-based link within 5 km of the farm's published location.
- **REPD offshore points are coarse.** Against Wikidata's coordinates, REPD placed Greater Gabbard 4 km away, but Hornsea 2 18 km, Moray West 19 km, Race Bank 22 km and Moray East 23 km away. Its own point for East Anglia 1 is 59 km from the farm. Several offshore sites share one point (East Anglia 1, 3 and 4; Hornsea 1, 3 and 4; Sofia and Dogger Bank C). Treat a `location_source` of `repd` offshore as a region, not a site. Onshore REPD points are site points.

## Known gaps

- **The Elexon gap is mostly closed, but a third of GB capacity still needs a person.** The dictionary and REPD cut GB's unmatched units from 156 to 46 (5% of MW). The `review` rows now hold 32% of MW. The largest:
  - **Dogger Bank A and B** (10 units, 2.4 GW) point at OSM's Dogger Bank C. Elexon calls them "Doggerbank OWF Project 1" and "Project 2", the dictionary has no REPD ID for them, and REPD lists A and B as one site.
  - **Hornsea 2** (3 units, 1.3 GW): none is in the dictionary, and Elexon names them after their owning companies (Breesea, Sonningmay, Soundmark). Breesea matches REPD's "Hornsea 2 - Optimus and Breesea" for review; the other two stay unmatched.
  - **Galloper**: one of its four units reports 386 MW in Elexon's data, so the units sum to nearly twice the farm.
  - **East Anglia One** is joined to Hornsea 1 through the dictionary error described above.
  - **Seagreen** and **Walney 1 and 2**: the units' summed capacity disagrees with the mapped farm's.

  A short, hand-checked override file would settle these better than more matching rules.
- **Farms missing from OSM as plants.** Newer farms, or farms mapped only as individual turbines, have no plant to match. In AEMO these include Uungula, MacIntyre, Wambo, Clarke Creek and Ryan Corner. In IESO they include Dillon and Railbed. Grouping OSM turbines into farms would recover some of them.
- **IESO capacity.** The IESO report gives each generator's hourly capability for one day, not its installed capacity. The prototype treats the day's highest figure as a floor, which can only rule a farm out.
- **Timing.** OSM shows today's map. Farms that were repowered or decommissioned need OSM's history to match older output.

## Licence

The CSVs in `output/` are derived from OpenStreetMap. They are © OpenStreetMap contributors and available under the [Open Database License](https://opendatacommons.org/licenses/odbl/). That is a share-alike licence, so anything built from these files must stay under the ODbL. Keep them separate from the catalogue entries, which are CC BY 4.0.

Rows in `elexon-bm.csv` whose `location_source` is `repd` take their farm name, capacity, status and coordinates from the Renewable Energy Planning Database, published by the Department for Energy Security and Net Zero under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Any reuse must keep this attribution: "Contains public sector information licensed under the Open Government Licence v3.0." The OGL allows this information to sit inside an ODbL file, as long as the attribution travels with it. The unit lists come from AEMO, Elexon and IESO under the terms recorded in their catalogue entries. The Power Station Dictionary is MIT-licensed. The code is MIT.
