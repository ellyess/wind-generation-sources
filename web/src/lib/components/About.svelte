<script lang="ts">
  import { REPO, store } from "../store.svelte";
  let year = $derived((store.cat?.generated ?? "2026").slice(0, 4));
  let cite = $derived(`Benmoufok, E. F. (${year}). Wind Generation Sources: an open, licence-annotated catalogue of observed wind power generation data. ${REPO}`);
  import CopyButton from "./CopyButton.svelte";
</script>

<div class="about">
  <article>
    <h1>About this catalogue</h1>
    <p class="lead">Where to find observed wind power generation, metered or reported by its publisher, country by country. Each entry
      says what the data are, how to get them, whether you may re-host them, and what goes wrong when you use them.</p>

    <h2>Why it exists</h2>
    <p>I spent a large part of my PhD tracking down observed wind generation data, scattered across grid operators, market
      operators, statistics offices and research archives, with licences and traps rarely written down. I had to list the sources
      out again for each piece of work. This catalogue publishes that list so you can start from it instead of repeating the
      search.</p>
    <p>— Ellyess F. Benmoufok</p>

    <h2>How the entries are made</h2>
    <dl>
      <dt>Observed output only</dt>
      <dd>Metered, settled, certified or reported by the publisher. Simulated series, such as renewables.ninja, EMHIRES or
        capacity factors from reanalysis, are left out.</dd>
      <dt>Licences are read, not inferred</dt>
      <dd>Each licence is read on the publisher's own page and dated. Until then, re-hosting stays <em>Unclear</em>.</dd>
      <dt>Every trap cites its evidence</dt>
      <dd>A trap is a property of the source, such as a mislabelled column, a silent change or a gap, linked to the documentation, issue or audit that shows it.</dd>
      <dt>Links, not copies</dt>
      <dd>The catalogue holds metadata only and never re-hosts a publisher's data. Live charts are fetched by your browser from
        publishers that allow it; nothing is stored.</dd>
      <dt>Checked by machine, and said so</dt>
      <dd>Links are requested weekly; one that refuses automated requests is reported as not judged, never as working.
        Annual totals are compared with a whole-fleet national figure, or else Eurostat or Ember, and each stated time step with the data.
        Entries a person has checked are marked <em>Reviewed</em>; the rest come from an automated research pass and are leads.
        <a class="lnk" {...store.link({ view: "checks" })}>Latest results</a></dd>
    </dl>

    <h2>The map</h2>
    <p>Countries are shaded by the finest level any source publishes: turbine, farm or plant, zone or company, or national total.
      Green marks data finer than a national total; grey, a national total only.</p>
    <p>Orange points are farms or turbines with their own published output and a known location. Where the publisher gives locations
      (Denmark's and Germany's turbine registers, EIA-860 in the US, the Brazilian, Swiss, Norwegian and Chilean operators, the research
      datasets), the point is theirs. Elsewhere each plant name was matched to a wind farm in OpenStreetMap (in Great Britain, also the
      Renewable Energy Planning Database), and Great Britain's balancing mechanism units are linked to farms through Wikidata (CC0) where
      it records the unit's ID. These links are unreviewed proposals; the tooltip says which kind a point is.</p>
    <p>In Great Britain, Ofgem-accredited stations with no confident match sit at their postcode's centre, drawn as hollow rings. That
      is not the turbine and can be a few kilometres off. Northern Ireland postcodes are not in the dataset, so those stations, and other
      plants with no confident match, have no point yet.</p>
    <p class="credits">Postcode centres from Ordnance Survey Code-Point Open under the Open Government Licence v3.0. Contains OS data
      © Crown copyright and database right 2026. Contains Royal Mail data © Royal Mail copyright and database right 2026. Contains National
      Statistics data © Crown copyright and database right 2026. Basemap by OpenFreeMap from OpenMapTiles and OpenStreetMap data;
      country outlines from Natural Earth, public domain.</p>

    <h2>Questions</h2>
    <div class="faq">
      <details>
        <summary>How accurate is this?</summary>
        <p>As good as the publishers, and each entry says where they fall short. Most entries and every map match come from an automated
          research pass and stay unreviewed until a person checks them, so expect the odd mistake. Each trap was checked against the
          publisher's own files or documentation and links to that evidence. Name-matched points are proposals; postcode points can be a
          few kilometres off.</p>
      </details>
      <details>
        <summary>Can I download the wind data here?</summary>
        <p>No; the data stay with their publishers. Each entry links to the download or API, and most have a short Python script that
          fetches a sample and reads its time stamps and units correctly.</p>
      </details>
      <details>
        <summary>Why do two sources give different totals for the same country?</summary>
        <p>Usually they measure different things: gross at the turbine or net to the grid, the whole fleet or only transmission-connected
          farms, a calendar or a fiscal year, metered values or the publisher's estimate. Sometimes one is simply wrong. The <a class="lnk" {...store.link({ view: "checks" })}>checks page</a>
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
        <p>Either no publisher of observed wind output was found for it, or the publisher names plants without locations and no confident
          match was found. Many publishers also block automated requests, so they could not be checked. Know a source? A pull request or
          an issue is welcome.</p>
      </details>
      <details>
        <summary>Is this simulated data?</summary>
        <p>No. Every source is metered, settled, certified or reported output. Modelled series built from weather data are left out on
          purpose: this is the observed record that models are tested against. A few sources are the publisher's own estimate of output
          it cannot meter, such as embedded wind; those say so under Measure.</p>
      </details>
    </div>

    <h2>Use it, cite it, fix it</h2>
    <p>Download the whole catalogue as <a href="./data/catalogue.csv" download>CSV</a> or <a href="./data/catalogue.json">JSON</a>.
      Entries are licensed CC BY 4.0, the code MIT; publishers' data stay under their own terms.</p>
    <div class="cite"><p>{cite}</p><CopyButton text={cite} what="citation" /></div>
    <p>Each source is one YAML file. Edit it and open a pull request; the validator checks the schema and house rules.
      <a href="{REPO}/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener">How to contribute</a>.</p>
    <p class="maint">Maintained by Ellyess F. Benmoufok.</p>
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
  .credits { font-size: 13px; color: var(--ink-3); }
  .maint { margin-top: 12px; font-size: 13px; color: var(--ink-3); }
  @media (max-width: 819px) { .about { padding: 24px 16px 48px; } }
</style>
