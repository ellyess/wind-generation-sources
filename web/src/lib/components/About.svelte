<script lang="ts">
  import { REPO, store } from "../store.svelte";
  let year = $derived((store.cat?.generated ?? "2026").slice(0, 4));
  let cite = $derived(`Benmoufok, E. (${year}). Wind Generation Sources: an open, licence-annotated catalogue of observed wind power generation data. ${REPO}`);
  import CopyButton from "./CopyButton.svelte";
</script>

<div class="about">
  <article>
    <h1>About this catalogue</h1>
    <p class="lead">Wind Generation Sources lists where to find observed wind power generation, metered or reported by its publisher,
      for each country. Every entry says what the data are, how to get them, whether you may re-host them, and what goes wrong when you use them.</p>

    <h2>How the entries are made</h2>
    <dl>
      <dt>Observed output only</dt>
      <dd>Every source is metered, settled, certified or reported by its publisher. Simulated series, such as renewables.ninja, EMHIRES or
        capacity factors computed from reanalysis, have other homes and are left out.</dd>
      <dt>Licences are read, not inferred</dt>
      <dd>Each licence was read on the publisher's own page on the date shown. Until it has been read, re-hosting stays <em>Unclear</em>.</dd>
      <dt>Every trap cites its evidence</dt>
      <dd>A trap is a property of the source: a mislabelled column, a silent change, a gap. Each one links to the documentation, issue or audit that shows it.</dd>
      <dt>Links, not copies</dt>
      <dd>The catalogue holds metadata only and never re-hosts a publisher's data. The live charts are fetched by your browser straight from
        publishers that allow it, and nothing is stored.</dd>
      <dt>Checked by machine, and said so</dt>
      <dd>Every link is requested again each week; a link that refuses automated requests is reported as not checked, never as working.
        Annual totals are compared with a national figure for the whole wind fleet where there is one, otherwise Eurostat or Ember, and the time step found in the data with the one the entry states.
        Entries a person has checked against the publisher's pages are marked <em>Reviewed</em>; the rest were compiled by an automated research pass and are leads until checked.
        <button type="button" class="lnk" onclick={() => store.go({ view: "checks" })}>See the latest results.</button></dd>
    </dl>

    <h2>The map</h2>
    <p>Each country is shaded by the finest level any catalogued source publishes: per turbine, per farm or plant, per zone or company, or a
      national total. Blue marks data finer than a country total; countries with only a national total are grey. Orange points are farms or turbines whose own output is published and whose location is known. Where the publisher
      gives locations (Denmark's and Germany's turbine registers, EIA-860 in the US, the Brazilian, Swiss, Norwegian and Chilean operators, the
      research datasets), the point is theirs. Elsewhere the publisher names its plants but gives no location, so each name was matched to a
      wind farm in OpenStreetMap (or, in Great Britain, the Renewable Energy Planning Database). Great Britain's balancing mechanism units are linked to their farms through Wikidata (CC0) where it records the unit's ID. All these links are unreviewed proposals, and the
      tooltip says which kind a point is. In Great Britain, Ofgem-accredited stations whose names found no confident match are placed
      at the postcode the register gives for them, drawn as hollow rings: that is the postcode's centroid, not the turbine, and can be a few
      kilometres off. Postcode centroids are from Ordnance Survey Code-Point Open under the Open Government Licence v3.0. Contains OS data
      © Crown copyright and database right 2026. Contains Royal Mail data © Royal Mail copyright and database right 2026. Contains National
      Statistics data © Crown copyright and database right 2026. Northern Ireland postcodes are not in that dataset, so those stations, and
      other plants with no confident match, have no point yet. Basemap by OpenFreeMap from OpenMapTiles and OpenStreetMap data;
      country outlines from Natural Earth, public domain.</p>

    <h2>Questions</h2>
    <div class="faq">
      <details>
        <summary>How accurate is this?</summary>
        <p>The data are as good as their publishers, and each entry says where they fall short. Most entries and every map match were
          compiled by an automated research pass and are marked <em>Unreviewed</em> until a person has checked them, so expect the odd
          mistake. The traps were each checked against the publisher's own files or documentation, and each links to that evidence.
          Map points matched by name are proposals, and postcode points can be a few kilometres off.</p>
      </details>
      <details>
        <summary>Can I download the wind data here?</summary>
        <p>No. The catalogue says where the data are and how to read them; the data stay with their publishers. Each entry links to the
          download or API, and most have a short Python script that fetches a sample and reads its time stamps and units correctly.</p>
      </details>
      <details>
        <summary>Why do two sources give different totals for the same country?</summary>
        <p>Usually because they measure different things: gross output at the turbine or net output to the grid, the whole fleet or only
          farms connected to the transmission grid, a calendar year or a fiscal one, metered values or the publisher's estimate. Sometimes
          one of them is simply wrong. The <button type="button" class="lnk" onclick={() => store.go({ view: "checks" })}>checks page</button>
          compares them, and the traps say which explanation applies.</p>
      </details>
      <details>
        <summary>Which source should I use?</summary>
        <p>Start with the finest level you need (turbine, farm, zone or national), then check the time step, whether you may re-host the
          data, and the traps. For a national total, a national publisher usually beats a global compilation; for a single farm, the
          operator's own data or a research dataset beats a match from a national list.</p>
      </details>
      <details>
        <summary>Why is a country or a wind farm missing?</summary>
        <p>Either no publisher was found that reports observed wind output for it, or its publisher names plants without saying where they
          are and no confident match was found. Many publishers also block automated requests, so they could not be checked. If you know
          a source, a pull request or an issue is welcome.</p>
      </details>
      <details>
        <summary>Is this simulated data?</summary>
        <p>No. Every source is output that was metered, settled, certified or reported. Modelled series built from weather data are left
          out on purpose, because the point of this catalogue is the observed record that models are tested against.</p>
      </details>
    </div>

    <h2>Use it, cite it, fix it</h2>
    <p>Download the whole catalogue as <a href="./data/catalogue.csv" download>CSV</a> or <a href="./data/catalogue.json">JSON</a>.
      Entries are licensed CC BY 4.0, the code MIT; publishers' data stay under their own terms.</p>
    <div class="cite"><p>{cite}</p><CopyButton text={cite} what="citation" /></div>
    <p>Each source is one YAML file. To add or correct one, edit it and open a pull request; the validator checks the schema and the house rules.
      <a href="{REPO}/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener">How to contribute</a>.</p>
    <p class="maint">Maintained by Ellyess Benmoufok.</p>
  </article>
</div>

<style>
  .about { overflow-y: auto; height: 100%; padding: 36px 28px 64px; }
  article { max-width: 62ch; margin: 0 auto; display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; overflow-wrap: break-word; font-size: 15px; color: var(--ink-2); }
  h1 { font-size: 28px; letter-spacing: -0.02em; color: var(--ink); }
  h2 { font-size: 17px; color: var(--ink); margin-top: 18px; }
  .lead { font-size: 16.5px; color: var(--ink); line-height: 1.55; }
  dl { margin: 0; display: grid; gap: 4px; }
  dt { font-weight: 600; color: var(--ink); margin-top: 8px; }
  dd { margin: 0; }
  .cite { display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); font-size: 13.5px; }
  .cite p { flex: 1; }
  .lnk { border: 0; background: none; padding: 0; color: var(--accent-ink); text-decoration: underline; text-underline-offset: 0.18em; }
  .faq { display: grid; border-top: 1px solid var(--line); }
  .faq details { border-bottom: 1px solid var(--line); }
  .faq summary { cursor: pointer; padding: 10px 0; font-weight: 600; color: var(--ink); }
  .faq summary:focus-visible { outline: 2px solid var(--accent-ink); outline-offset: 2px; }
  .faq details p { padding: 0 0 12px; }
  .maint { margin-top: 12px; font-size: 13px; color: var(--ink-3); }
  @media (max-width: 819px) { .about { padding: 24px 16px 48px; } }
</style>
