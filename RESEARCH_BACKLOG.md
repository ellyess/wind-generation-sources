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

Leads left after the two research passes of 2026-11-08. The first added 17 entries (Canada CCEI;
Italy, Portugal, Sweden x2, North Macedonia and Russia; South Korea x3, Sri Lanka, Kazakhstan,
Mongolia and Jordan; South Africa, Kenya and Mauritius). The second added 8 (Switzerland Pronovo,
Lithuania, Romania, Bulgaria, Prince Edward Island, KOEN, Azerbaijan and SDWPF) and extended
`mn-erc-energy-statistics` to 2025.

### Americas
- **Puerto Rico:** Polaris Infrastructure's reports name Punta Lima (26 MW) output; check whether
  they give a usable series. EIA-923 does not cover the island.
- **Prince Edward Island:** the PEIEC annual reports before those in
  `ca-pe-peiec-annual-report-wind-farms` may extend it back.
- **sieLAC:** confirm which wind series `lac-olacde-sielac` holds; the data pages ask for
  credentials (not registered).
- **Honduras:** CND publishes through a mobile app only; no web route found.
- **Not added, for the record:** Nova Scotia Power, NB Power and SaskPower show the current day
  only or no wind column; Hawaiian Electric's page is gone; Guatemala's AMM BI portal embeds
  credentials in the page (not used); Ecuador lumps wind or needs a certificate.

### Europe
- **Bulgaria:** NSI monthly wind starts in January 2026 (`bg-nsi-monthly-electricity-production`);
  look again for an earlier series once the entry has a year behind it.
- **Lithuania and Romania:** the licence pages returned 403, so both entries carry an unverified
  licence. ANRE would not connect.
- **Not added, for the record:** Czechia OTE (subsidised volume only), Serbia AERS and EPS (PDF,
  covered by `rs-ems`), SEMO BM-151 and BM-152 (the same as BM-086 D+1 and D+5).

### Asia and the Middle East
- **Japan:** OCCTO unit output needs a person to accept the disclaimer (see above).
- **South Korea:** KOEN's keyed API and its joint-venture farms; KOMIPO's regional wind API
  (15157017) needs a key.
- **Saudi Arabia:** the GASTAT figure for Dumat al-Jandal (1,588 GWh in 2022) is an expected
  yield, not observed generation. Not added.
- **Philippines:** the DOE PDF paths return "Page Not Found".
- **Only press figures found:** Oman, UAE, Kuwait, Iran, Uzbekistan.

### Africa
- **South Africa:** Stats SA electricity tables sit behind a bot check (not bypassed).
- **Namibia:** NamPower lumps wind; the ECB bulletin rounds it to whole GWh. Later bulletins may
  split it.
- **Not added, for the record:** IPP Office reports (404), SAWEA, NERSA, AFREC and the power pools
  (SAPP, EAPP, WAPP), SOMELEC and Djibouti had no usable wind series.

### Open turbine datasets
- **Levenmouth demonstration turbine** (ORE Catapult): paid access, and the site's TLS certificate
  has expired.
- **EDP open data:** the download returns 403.

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
- Corrected the same day: `cl-cen` (the host is in the specification's key description) and
  `es-ree-esios-real-time-wind` (the no-date request now also answers 403). On 2026-11-08 the
  `eu-entsoe` conventions note was given ENTSO-E's documented position-to-time formula.

## Map points still missing

`crosswalk/output/lists.json` counts, for every unit list, how many units were placed. Units
marked `review` or `unmatched` in `crosswalk/output/<entry>.csv` have no point yet; each row's
`runner_up` and `notes` say why. Larger gaps on 6 November 2026:

- **Costa Rica (CENCE, both entries):** apps.grupoice.com returns 403 to automated requests, so no unit list.
- **Brazil, CCEE:** the dataset page, API and downloads return 403 "Acesso bloqueado". The ONS entries cover the same fleet.
- **Greece, IPTO:** the SCADA file gives no technology. The 90 units listed are presumed wind (untagged renewables with output at night), and only names that matched an OpenStreetMap wind farm got a point. Confirm against a list of wind units before trusting the rest.
- **Ofgem RER:** on 7 November 2026 stations with no confident OpenStreetMap farm were placed at their postcode centroid (OS Code-Point Open, shown as hollow rings on the map), and 591 of 1,882 now have a point. 1,291 remain: 817 have Northern Ireland postcodes, which Code-Point Open does not cover (ONS's NI postcode data is for internal business use only), 458 have no postcode, 11 are offshore and 5 postcodes are not found. On 8 November the two flagged matches were settled in `crosswalk/corrections.csv`: KIRKSTANTON AIRFIELD moved from Airfield Farm (Bedfordshire) to Haverigg (Cumbria), and West Durham kept, as its name and capacity match.
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
- South Africa: settled on 8 November. CSIR's statistics from Eskom data give 11.1 TWh for 2024, now the national reference; Ember agrees and IRENA's 0.331 TWh is far off (it may hold only Eskom's 100 MW Sere farm, not proven; trap added).

Since 7 November 2026 the reference is a national figure for the whole wind fleet in the calendar
year where one exists, then Eurostat, then Ember. Live national readers are used for Spain, France
and Denmark; curated figures, each quoted with its URL in `checks/national-figures-2024.yaml`,
for Kenya, Kazakhstan, Sri Lanka, Mongolia, Peru and Russia. Germany (SMARD), Great Britain
(transmission only), Belgium (Elia's upscaled estimate) and New Zealand (grid-connected only) are
not used, and Bosnia and Herzegovina's DERK figure covers only transmission-connected plants.
`wgs check agreement` re-applies the rule to the saved totals without fetching anything.

## Verification doubts, 2026-11-08

The verification pass of 2026-11-08 re-read every entry against its source. These points could not
be settled without a person:

- **Unreachable or blocked:** `cv-electra` (site unreachable); `dk-orsted` (403); the Energy
  Institute and IRENA terms pages (blocked); ISO New England's report page (captcha; the workbook
  link works); Litgrid (expired TLS); the Lithuanian and Romanian terms pages (403).
- **Seen only through a proxy:** CCEE and both CENCE entries were read through a search-engine
  cache, not the publisher's site. Their claims stand but are unconfirmed at source.
- **Latvia (`lv-ast`):** Cloudflare refused plain requests; the verifier opened the page in a
  browser, which loaded without a challenge. No check was bypassed.
- **Licence still open:** PSE (Poland) data terms.
- **Lags to watch:** REN (Portugal) publication lag; CEA (India) weekend gaps; the Swissgrid CSV may
  not have been refreshed this year.
- **Figures to re-read:** Kenya's Figure 3.6 month order; the UEP I rows in Panama's reports; the
  Kelmarsh claim that each file holds 81 blocks.
- **Japan OCCTO:** needs a disclaimer accepted by hand before any data shows.

## Decisions for the maintainer

- **Ember and EIA, gross or net:** Ember's methodology calls EIA's data gross generation; EIA labels it net. Noted in the Ember yearly and EIA entries; `world-ember-monthly` could note it too.
- **Kelmarsh v4:** the new trap cites a published audit. Confirm it against the 2023 files, and check whether Penmanshiel has the same layout.
- **Ember monthly:** its countries list holds Europe only, though the dataset is wider.
- **Ofgem:** the register may be renamed "Renewable Electricity Register"; update the entry title
  if so.

Decided on 2026-11-07:
- **Danish turbine points:** kept on the map with credit to the Danish Energy Agency and a link to
  the register. Converting coordinates to latitude and longitude is treated as a change of
  format, not of content.
- **ISO New England snippet:** kept. It downloads the yearly workbook from the direct link the
  entry lists, which asks for no captcha; only the report page shows one.
- **Panama:** the key embedded in CND's public page is not used. Ask CND for documented access.
- **Energy Institute:** redistribution changed from "prohibited" to "unclear", because the terms
  found are site-wide rather than specific to the dataset. Link to the EI rather than re-hosting.

Decided on 2026-11-08:
- **PJM:** redistribution changed from "unclear" to "prohibited". The Data Miner 2 API guide says
  its data are "for internal use only" and redistribution "is strictly prohibited without a PJM
  membership".
- **EIA licence:** `allowed-with-attribution` for every EIA entry, because EIA asks for an
  acknowledgment. `us-eia-923` and `us-eia-930` changed.
- **Fixed releases:** a new status, `fixed-release`, for datasets released once as a closed set.
  13 entries moved: the 11 one-off releases marked `active`, plus `cn-sdwpf` and
  `fr-engie-la-haute-borne`. `eu-opsd`, `is-hagstofa`, `no-nve` and `se-svk` stay `discontinued`,
  as series that were updated and then stopped. Like `discontinued`, it needs a coverage end.
- **Permission-required redistribution:** a new value for terms that allow re-hosting once the
  publisher agrees and say how to ask. Four entries moved from `link-only`: `ec-arconel`,
  `in-cea`, `de-netztransparenz` and `eu-entsoe`. Plain "all rights reserved without permission"
  notices keep their earlier value.
- **Jordan NEPCO:** `link-only`.
- **Altahullion:** resolution `1min`, with a trap that the one-minute file covers T11 only.
- **Theme:** dark only.
- **Japan TSO snippet:** the Kyushu shift stays. Its labels run 0:30 to 24:00, and "24:00" can
  only mark the end of a half hour, so moving it back 30 minutes is safe without documentation.
- **SCADA measure:** SCADA readings from the operator's control system are `reported-generation`;
  `metered-energy` is for revenue or settlement meters. The schema says so. `co-xm` stays
  `metered-energy`: dataset 055A4D is XM's settlement data, and its SCADA estimate is a separate
  dataset (E17D25).
- **Snippets with an unknown value type:** they no longer turn MW into energy. Hydro-Québec, PJM,
  ENTSO-E, Fingrid, REE real time, PSE and REN now print mean and peak MW instead of GWh.
  AESO and NVE keep `wind_mwh`, and UFSC `power_kw`, because each docstring states the assumption
  and its evidence.
