<script lang="ts">
  import { CONTINENTS, store } from "../store.svelte";
  import { fold, plural } from "../text";
  import Icon from "./Icon.svelte";
  import Filters from "./Filters.svelte";
  import LevelDot from "./LevelDot.svelte";
  import SourceCard from "./SourceCard.svelte";

  let traps = $derived(store.sources.reduce((n, s) => n + (s.traps ?? []).length, 0));
  let groups = $derived.by(() => {
    const g = new Map<string, { code: string; n: number; tier: number }[]>();
    const counts = new Map<string, number>();
    for (const s of store.filtered) for (const c of s.countries) counts.set(c, (counts.get(c) ?? 0) + 1);
    for (const code of store.catalogued) {
      const cont = store.continentOf(code);
      if (store.region && cont !== store.region) continue;
      if (!g.has(cont)) g.set(cont, []);
      g.get(cont)!.push({ code, n: counts.get(code) ?? 0, tier: store.tiers.get(code) ?? 0 });
    }
    for (const list of g.values()) list.sort((a, b) => store.placeName(a.code).localeCompare(store.placeName(b.code)));
    return [...CONTINENTS, "Elsewhere"].filter((c) => g.has(c)).map((c) => ({ name: c, list: g.get(c)! }));
  });
  let searching = $derived(store.q.trim().length > 0);
  // Honest aggregate trust figures, computed from the entries rather than claimed.
  let read = $derived(store.sources.filter((s) => s.licence.verified).length);
  let reviewed = $derived(store.sources.filter((s) => s.reviewed !== false).length);
  let fine = $derived(new Set(store.sources.filter((s) => s._tier <= 2).flatMap((s) => s.countries)).size);
  let linksChecked = $derived(store.checks.links?.checked);
  // A query that names a country offers that country first.
  let places = $derived.by(() => {
    const q = fold(store.q.trim());
    if (q.length < 2) return [];
    return [...store.catalogued].filter((c) => fold(store.placeName(c)).includes(q))
      .sort((a, b) => Number(!fold(store.placeName(a)).startsWith(q)) - Number(!fold(store.placeName(b)).startsWith(q))
        || store.placeName(a).localeCompare(store.placeName(b))).slice(0, 4);
  });
  // Results lead with the finest data.
  let results = $derived(store.filtered.slice().sort((a, b) => a._tier - b._tier || a.id.localeCompare(b.id)));
</script>

<div class="overview">
  <header>
    <h1>Observed wind generation, country by country</h1>
    <p class="lead">
      Where to find <strong>metered or reported</strong> wind power output: what each source publishes, whether you may
      re-host it, and the traps others have hit. <span class="num">{store.sources.length}</span> sources for
      <span class="num">{store.catalogued.size}</span> countries, <span class="num">{fine}</span> of them with output per farm or
      per turbine; <span class="num">{traps}</span> traps recorded with evidence.
    </p>
    <ul class="trust">
      <li><span class="num">{read}</span> licences read on the publisher's page; the other <span class="num">{store.sources.length - read}</span> stay Unclear until read.</li>
      <li><span class="num">{reviewed}</span> entries reviewed by a person; the rest are leads from an automated research pass.</li>
      <li>Links and Python snippets rechecked by machine{linksChecked ? `, last on ${linksChecked}` : " every week"}.
        <button type="button" class="lnk" onclick={() => store.go({ view: "checks", country: "", source: "" })}>How it is checked</button></li>
    </ul>
  </header>

  <Filters />

  {#if searching || store.activeFilters > 1}
    {#if places.length}
      <ul class="places" aria-label="Countries matching the search">
        {#each places as c (c)}
          <li><button type="button" onclick={() => store.go({ country: c, source: "" })}>
            <LevelDot tier={store.tiers.get(c) ?? 0} size={10} /><span>Go to <strong>{store.placeName(c)}</strong></span><Icon name="chev" size={14} />
          </button></li>
        {/each}
      </ul>
    {/if}
    <div class="cards">
      {#each results.slice(0, 60) as s (s.id)}<SourceCard {s} />{/each}
      {#if store.filtered.length > 60}<button type="button" class="more" onclick={() => store.go({ view: "sources" })}>Show all {store.filtered.length} in the table</button>{/if}
    </div>
  {:else}
    {#each groups as g (g.name)}
      <section>
        <h2>{g.name} <span class="num">{g.list.length}</span></h2>
        <ul class="clist">
          {#each g.list as c (c.code)}
            <li>
              <button type="button" class:zero={!c.n} onclick={() => store.go({ country: c.code, source: "" })}>
                <LevelDot tier={c.tier} size={10} /><span class="nm" title={store.placeName(c.code)}>{store.placeName(c.code)}</span><span class="n num">{c.n}</span>
              </button>
            </li>
          {/each}
        </ul>
      </section>
    {/each}
    {#if !groups.length}<p class="empty">No country matches these filters.</p>{/if}
    <p class="hint">Pick a country on the map or in the list for its sources, coverage, live output and cross-checks. Shading shows the finest level of {plural(store.filtered.length, "source")} under the filters.</p>
  {/if}
</div>

<style>
  .overview { display: grid; grid-template-columns: minmax(0, 1fr); gap: 18px; }
  header { display: grid; gap: 8px; }
  h1 { font-size: 22px; letter-spacing: -0.02em; line-height: 1.2; }
  .lead { font-size: 14px; color: var(--ink-2); line-height: 1.55; }
  .lead strong { color: var(--ink); font-weight: 600; }
  .trust { list-style: none; margin: 2px 0 0; padding: 10px 0 0; display: grid; gap: 4px; border-top: 1px solid var(--line);
    font-size: 12.5px; color: var(--ink-2); }
  .trust li { padding-left: 14px; position: relative; }
  .trust li::before { content: ""; position: absolute; left: 2px; top: 0.6em; width: 5px; height: 5px; border-radius: 50%; background: var(--line-strong); }
  .lnk { border: 0; background: none; padding: 0; color: var(--accent-ink); font-weight: 500; text-decoration: underline; text-underline-offset: 0.18em; text-decoration-thickness: 1px; }
  .lnk:hover { text-decoration-thickness: 2px; }
  .places { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
  .places button { display: grid; grid-template-columns: 10px minmax(0, 1fr) 14px; align-items: center; gap: 8px; width: 100%; height: 36px;
    padding: 0 10px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); text-align: left; font-size: 13.5px; color: var(--ink-2); }
  .places button:hover { border-color: var(--line-strong); color: var(--ink); }
  .places strong { color: var(--ink); font-weight: 600; }
  .places :global(.ic) { color: var(--ink-3); }
  section { display: grid; gap: 6px; }
  h2 { font-size: 13px; font-weight: 600; color: var(--ink-2); display: flex; gap: 6px; align-items: baseline; }
  h2 .num { font-weight: 400; color: var(--ink-3); }
  .clist { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 12px; }
  .clist button { display: grid; grid-template-columns: 10px 1fr auto; align-items: center; gap: 8px; width: 100%;
    padding: 5px 6px; border: 0; background: none; text-align: left; border-radius: var(--radius-sm); font-size: 13.5px; }
  .clist button:hover { background: var(--surface-3); }
  .clist button.zero { color: var(--ink-3); }
  .nm { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .n { font-size: 12px; color: var(--ink-3); }
  .cards { display: grid; gap: 8px; }
  .more { height: 36px; border: 1px solid var(--line-strong); border-radius: var(--radius); background: var(--surface); font-weight: 500; }
  .hint, .empty { font-size: 12.5px; color: var(--ink-3); }
</style>
