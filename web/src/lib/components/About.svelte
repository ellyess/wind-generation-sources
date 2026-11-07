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
        Annual totals are compared with Eurostat or Ember, and the time step found in the data with the one the entry states.
        Entries compiled by an automated research pass are marked <em>Unreviewed</em> until a person has checked them.
        <button type="button" class="lnk" onclick={() => store.go({ view: "checks" })}>See the latest results.</button></dd>
    </dl>

    <h2>The map</h2>
    <p>Each country is shaded by the finest level any catalogued source publishes: per turbine, per farm or plant, per zone or company, or a
      national total. Orange points are farms or turbines whose own output is published and whose location is known. Where the publisher
      gives locations (Denmark's and Germany's turbine registers, EIA-860 in the US, the Brazilian, Swiss, Norwegian and Chilean operators, the
      research datasets), the point is theirs. Elsewhere the publisher names its plants but gives no location, so each name was matched to a
      wind farm in OpenStreetMap (or, in Great Britain, the Renewable Energy Planning Database); those links are unreviewed proposals, and the
      tooltip says which kind a point is. Plants whose names found no confident match have no point yet. Basemap by OpenFreeMap from OpenMapTiles and OpenStreetMap data;
      country outlines from Natural Earth, public domain.</p>

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
  article { max-width: 70ch; margin: 0 auto; display: grid; gap: 14px; font-size: 15px; color: var(--ink-2); }
  h1 { font-size: 28px; letter-spacing: -0.02em; color: var(--ink); }
  h2 { font-size: 17px; color: var(--ink); margin-top: 18px; }
  .lead { font-size: 16.5px; color: var(--ink); line-height: 1.55; }
  dl { margin: 0; display: grid; gap: 4px; }
  dt { font-weight: 600; color: var(--ink); margin-top: 8px; }
  dd { margin: 0; }
  .cite { display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); font-size: 13.5px; }
  .cite p { flex: 1; }
  .lnk { border: 0; background: none; padding: 0; color: var(--accent-ink); text-decoration: underline; text-underline-offset: 0.18em; }
  .maint { margin-top: 12px; font-size: 13px; color: var(--ink-3); }
  @media (max-width: 819px) { .about { padding: 24px 16px 48px; } }
</style>
