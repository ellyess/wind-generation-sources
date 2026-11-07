# Research backlog

Leads found during the research pass of 2026-11-06 but not added, and cross-check results that
need a person. Each line says why it was left out. Pick one, verify it under the rules in
`CONTRIBUTING.md`, and open a pull request.

## Needs a person with a browser

These sites refused automated requests (Cloudflare challenges, 403, expired TLS). The research pass
did not bypass them.

- **Cyprus:** TSO Cyprus, CERA.
- **Albania:** OST.
- **Ukraine:** Ukrenergo.
- **Iceland:** Orkustofnun PDFs.
- **Israel:** Noga ISO.
- **Vietnam:** NSMO daily reports (nsmo.vn).
- **India:** Grid-India daily power supply position reports.
- **China:** data.stats.gov.cn provincial monthly wind (403); likely finer than the national entry.
- **Egypt:** NREA annual report (expired TLS certificate).
- **Morocco:** ONEE.
- **Tunisia:** STEG.
- **South Africa:** Stats SA P4141.
- **Japan:** OCCTO unit output disclosure (hatsuden-kokai.occto.or.jp). It has 30-minute output per unit of 100 MW or more; the licence is free use with attribution. It needs a disclaimer accepted by hand. Check whether any wind units are listed (Ishikari Bay offshore, 112 MW).

- **United States, ERCOT and SPP:** both refused connections from outside the US (Incapsula 403; SPP timed out). ERCOT's API specification (github.com/ercot/api-specs) documents three products, each needing a free subscription key:
  - NP4-732-CD: hourly wind by load zone.
  - NP4-742-CD: hourly wind by region.
  - NP3-965-ER: the 60-day SCED disclosure, per resource.
  Until someone checks from a US connection, `us-eia-930-hourly` is the only route.
- **Honduras, El Salvador, Venezuela:** the publisher sites were unreachable or returned 403.
- **Panama:** CND's daily and hourly reports by plant use a key embedded in the public page (sitioprivado.cnd.com.pa). Decided 2026-11-07: the key is not used. Ask CND for documented access first.

## Found, not yet added

### Americas
- **Canada:** the CCEI high-frequency electricity dataset (HFED) has wind for NS, PEI, QC, ON, SK and AB. It is a beta aggregator with known duplicates and gaps, and its API link was not found.
- **Canada, live display only:** Nova Scotia Power OASIS, NB Power and SaskPower show the current day with no history. Use `ca-statcan-monthly-generation-by-type` instead.
- **Hawaii and Puerto Rico:** check whether EIA-923 covers their wind plants. Hawaiian Electric's Renewable Watch is a live display only.
- **Guatemala:** the AMM BI portal (reportesbi.amm.org.gt) has not been checked.
- **Ecuador:** CENACE lumps wind into "non-conventional"; SIMEM needs a certificate.
- **Check these country lists:** `world-eia-international` lists AQ and AW but not CW or BQ. Check `lac-olacde-sielac` against what sieLAC actually holds for wind.

### Europe
- **Italy:** Terna annual production per region and province (dati.terna.it).
- **Portugal:** DGEG statistics.
- **Czechia:** OTE.
- **Lithuania:** Statistics Lithuania.
- **Serbia:** EPS, AERS.
- **Romania:** INS, ANRE.
- **Bulgaria:** NSI.
- **North Macedonia:** MakStat.
- **Switzerland:** BFE weekly data, Pronovo.
- **Sweden:** SCB monthly; Energimyndigheten county files.
- **Ireland:** SEMO BM-151 and BM-152 reports.
- **Russia:** SO-UPS monthly PDFs on renewable plants in the support scheme, wind included (so-ups.ru/fileadmin/files/company/markets/YYYY/res/).

### Asia and the Middle East
- **Sri Lanka:** PUCSL daily generation reports. Daily wind for the state utility and private producers, from 2016 to June 2024. They count telemetered plants only, and some wind plants are excluded. No listing page was found.
- **South Korea:** more generator-company files on data.go.kr, each under a "no restriction" licence:
  - Korea Midland Power, Sangmyeong (15119454);
  - KOSPO, Seongsan;
  - KOWEPO farm-level 2017-2023 (15106292). One hour in this file reads 1,044,900 for a 16 MW farm.
- **Philippines:** Department of Energy monthly generation by plant type per grid (the PDFs could not be read).
- **Not reached:** Kazakhstan (annual figures only), Mongolia, Jordan, Oman, Iran, Saudi Arabia, UAE, Kuwait, Azerbaijan, Uzbekistan.

### Africa
- **South Africa:**
  - IPP Office (REIPPPP) quarterly reports: every PDF returned 404.
  - SAWEA, NERSA.
- **Kenya:** KPLC annual reports (purchases per station).
- **Namibia:** NamPower annual reports. The ECB bulletin rounds wind to whole GWh.
- **Mauritius:** CEB (the site was redesigned and old statistics pages 404).
- **Not searched:** Mauritania (SOMELEC), Djibouti (Ghoubet), power pools (SAPP, WAPP, EAPP), AFREC.

### Open turbine datasets
- **SDWPF** (Baidu KDD Cup 2022, 134 turbines, CC BY 4.0): the publisher never states a country.
- **Levenmouth demonstration turbine** (ORE Catapult): the data site did not respond.
- **EDP open data:** the page returns 404.

## Time and unit conventions to confirm

Every entry's `conventions` block was read from the publisher on 6 November 2026 by an automated
research pass, and says so in its note. 48 entries leave the time stamp `unknown`, 37 the time
zone and 35 the value type, because the publisher does not state them.

The possible traps that pass found were checked against the publishers' own files and documents
on 7 November 2026. Those that held are now traps or field fixes in the entries, dated
2026-11-07 and marked not yet reviewed. That includes four corrections to existing traps: SEMO
values are MWh, not average MW; Chile follows daylight saving; Bulgaria's autumn change is not
handled correctly; IESO versions are month-to-date copies. Still open:

- `br-ccee-hourly-generation-by-plant`: a column possibly in MWh rather than MWmed. The site
  returned HTTP 403 ("Acesso bloqueado") and was not checked.
- `tr-epias-transparency`: +03:00 now, and possibly older daylight-saving rules before 2016. The
  API needs a login, so the data were not inspected.
- `us-nyiso-fuel-mix`: whether values are snapshots or interval averages. Neither the user's
  guide nor the data settle it, so the trap no longer says "instantaneous".
- `gt-amm-posdespacho-diario`: the daily total matches neither a sum nor a trapezoid of the
  hourly readings, so the value type is now `unknown`. It needs someone who can ask AMM.
- `au-aemo-nem-unit-scada`: the UTC+10 market time is stated on another MMS table's field, not on
  DISPATCH_UNIT_SCADA itself.
- `lt-litgrid-open-data-wind`: the API's TLS certificate had expired, so only the metadata were
  read. `cl-cen-generacion-real`: the trap's evidence is API responses saved by PyVWF in July
  2026; a keyless re-fetch returns HTTP 403.
- `es-ree-redata`: `unit` was set to MWh from the web page's GWh figures matching the API values
  divided by 1,000. That is the publisher's own label, but it is not stated on the API. Revert to
  `unknown` if rule 7 is read strictly.
- Not reached on 6 November: `lac-olacde-sielac` (needs a login), `world-ei` (bot check), and the
  Ofgem certificate download (HTTP 403).

## Found while writing snippets

On 7 November 2026 an automated pass wrote a Python snippet for each keyless source (see
`snippets/README.md`). Running them turned up about 30 disagreements with the entries. A second
pass the same day checked each against the publisher and wrote the confirmed ones into 26 entries
as new or corrected traps (each marked "not yet reviewed by a person"). Two changes matter most:
both `es-ree-esios-*` entries now have `key_required: true`, and `us-eia-923-plant-generation`
now says to keep "AM" records, which hold reported months for most wind plants from 2023.

Still open:
- `gb-altahullion-scada`: the time zone is not settled. The series spans only an autumn clock
  change, where a missing repeated hour proves nothing, and the dataset does not say.
- `fr-smarteole-scada`, `gr-underpin-wind-farm-scada`: the data contain an hour that local
  clocks skipped, so the stamps are not local time with daylight saving, but no document states
  UTC. `timezone` stays `unknown`.
- Assumed in snippets, not stated by the publisher (each docstring says so; nothing documents
  them): UTC-5 for `co-xm`, UTC-4 for `do-oc`, UTC-6 for `ni-cndc`, period starts for `no-nve`,
  `nordic-esett` and `pt-ren`. `gr-ipto` and `gt-amm` are indexed by the published hour label.

**No snippet**
- HTTP 403 or a bot check: `br-ccee`, `cn-nbs`, `cr-cence` (both), `cv-electra`, `lv-ast`,
  `world-ei`, `gb-ofgem` certificates.
- Login or form session: `world-iea`, `mx-cenace`.
- Expired certificate: `lt-litgrid`.
- On request under an NDA: `dk-orsted`.
- PDF tables that do not extract cleanly: `jm-mset`, `ma-mtedd`, `pk-cppa`.
- Chart-only values: `ke-epra`.
- Keyed: since 7 November 2026 all 9 keyed entries have a snippet that reads its key from an
  environment variable (`# wgs: needs ...`). None has run against live data. The ENTSO-E key on
  the maintainer's machine returned HTTP 401 "Authentication failed." (regenerate it or check
  API access is approved); its parser was checked on ENTSO-E's documented example response. The
  other 8 were written from the publishers' API documentation without a key. `tr-epias` and
  `lac-olacde-sielac` use a documented username and password token flow; the sieLAC snippet
  reads wind "Production" from the energy balance, which may not be the series the entry
  describes.

**Found while writing the keyed snippets (not yet written into the entries)**
- `us-pjm-wind-generation`: the Data Miner 2 API guide says "redistribution of information and
  or data contained in or derived from Data Miner is strictly prohibited without a PJM
  membership". The entry says `unclear`; a licence change is a maintainer decision.
- `eu-entsoe-actual-generation`: the conventions note says position-to-time mapping is not
  documented, but ENTSO-E's curve-type document gives "TimeStepPosition =
  StartDateTimeofTimeInterval + ( Resolution * ( Pos − 1))".
- Corrected the same day: `cl-cen` (the host is in the specification's key description) and
  `es-ree-esios-real-time-wind` (the no-date request now also answers 403).

## Map points still missing

`crosswalk/output/lists.json` counts, for every unit list, how many units were placed. Units
marked `review` or `unmatched` in `crosswalk/output/<entry>.csv` have no point yet; each row's
`runner_up` and `notes` say why. Larger gaps on 6 November 2026:

- **Costa Rica (CENCE, both entries):** apps.grupoice.com returns 403 to automated requests, so no unit list.
- **Brazil, CCEE:** the dataset page, API and downloads return 403 "Acesso bloqueado". The ONS entries cover the same fleet.
- **Greece, IPTO:** the SCADA file gives no technology. The 90 units listed are presumed wind (untagged renewables with output at night), and only names that matched an OpenStreetMap wind farm got a point. Confirm against a list of wind units before trusting the rest.
- **Ofgem RER:** on 7 November 2026 stations with no confident OpenStreetMap farm were placed at their postcode centroid (OS Code-Point Open, shown as hollow rings on the map), and 591 of 1,882 now have a point. 1,291 remain: 817 have Northern Ireland postcodes, which Code-Point Open does not cover (ONS's NI postcode data is for internal business use only), 458 have no postcode, 11 are offshore and 5 postcodes are not found. Two existing matches look wrong and carry a "check:" note: KIRKSTANTON AIRFIELD (284 km from its postcode) and West Durham (21 km).
- **Brazil, ONS generation by plant:** 103 older single plants have no coordinates in ONS's capacity-factor dataset and no confident OpenStreetMap match.
- **Germany:** 461 units in the movement data had no wind unit in the Marktstammdatenregister export.
- **Greece, underpin dataset:** the farm is anonymous, so it cannot be placed.

## Cross-check flags to confirm

The 2024 annual cross-check (`checks/agreement-2024.json`) put eleven countries more than 30% from
the reference. On 7 November 2026 each was checked against the national publisher, and the
outliers are now traps in `world-eia-international`, `world-irena-irenastat`,
`world-ember-monthly` and `world-ember-yearly`. The national figure supported:

- **Ember** in Kenya (EPRA 1,797.67 GWh; IRENA is low) and Bangladesh (BPDB 69 and 99 million kWh
  for the fiscal years; EIA is low).
- **Ember and IRENA** in Colombia, Peru, Kazakhstan and Pakistan (EIA is off).
- **EIA** in Russia (SO-UPS 8,794.1 million kWh; Ember and IRENA are low).
- **EIA and IRENA** in Sri Lanka and Mongolia, and **Eurostat and IRENA** in Bosnia and Herzegovina
  and Moldova (Ember's monthly series is off; in Mongolia it is all renewables).

Still open:
- The cause of each EIA gap, IRENA's Kenya and Russia values, and Ember's Sri Lanka and Russia
  series. Stale figures are suspected for EIA in Peru and Bangladesh, but nothing is proven.
- Moldova: whether Ember's ENTSO-E series covers only the 40.84 MW on the transmission grid
  (checking needs an ENTSO-E key). ANRE's site refused connections.
- Pakistan and Bangladesh: no calendar-year national figure was found, only fiscal years.
- South Africa is also flagged: IRENA gives 0.331 TWh against Ember 11.135 and EIA 12.574. IRENA has not been checked against Eskom or NERSA.

Since 7 November 2026 the reference is a national figure for the whole wind fleet in the calendar
year where one exists, then Eurostat, then Ember. Live national readers are used for Spain, France
and Denmark; curated figures, each quoted with its URL in `checks/national-figures-2024.yaml`,
for Kenya, Kazakhstan, Sri Lanka, Mongolia, Peru and Russia. Germany (SMARD), Great Britain
(transmission only), Belgium (Elia's upscaled estimate) and New Zealand (grid-connected only) are
not used, and Bosnia and Herzegovina's DERK figure covers only transmission-connected plants.
`wgs check agreement` re-applies the rule to the saved totals without fetching anything.

## Decisions for the maintainer

- **Ember and EIA, gross or net:** Ember's methodology calls EIA's data gross generation; EIA labels it net. Noted in the Ember yearly and EIA entries; `world-ember-monthly` could note it too.
- **Kelmarsh v4:** the new trap cites a published audit. Confirm it against the 2023 files, and check whether Penmanshiel has the same layout.

Decided on 2026-11-07:
- **Danish turbine points:** kept on the map with credit to the Danish Energy Agency and a link to
  the register. Converting coordinates to latitude and longitude is treated as a change of
  format, not of content.
- **ISO New England snippet:** kept. It downloads the yearly workbook from the direct link the
  entry lists, which asks for no captcha; only the report page shows one.
- **Panama:** the key embedded in CND's public page is not used. Ask CND for documented access.
- **Energy Institute:** redistribution changed from "prohibited" to "unclear", because the terms
  found are site-wide rather than specific to the dataset. Link to the EI rather than re-hosting.
