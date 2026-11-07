<script lang="ts">
  import { CONTINENTS, store } from "../store.svelte";
  import { plural } from "../text";
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
</script>

<div class="overview">
  <header>
    <h1>Observed wind generation, country by country</h1>
    <p class="lead">
      Where to find <strong>metered or reported</strong> wind power output, with the licence of every source read on the
      publisher's page and the known traps of each, with evidence. <span class="num">{store.sources.length}</span> sources,
      <span class="num">{store.catalogued.size}</span> countries, <span class="num">{traps}</span> traps recorded.
    </p>
  </header>

  <Filters />

  {#if searching || store.activeFilters > 1}
    <div class="cards">
      {#each store.filtered.slice(0, 60) as s (s.id)}<SourceCard {s} />{/each}
      {#if store.filtered.length > 60}<button type="button" class="more" onclick={() => store.go({ view: "sources" })}>Show all {store.filtered.length} in the table</button>{/if}
    </div>
  {:else}
    {#each groups as g (g.name)}
      <section>
        <h2>{g.name} <span class="num">{g.list.length}</span></h2>
        <ul>
          {#each g.list as c (c.code)}
            <li>
              <button type="button" class:zero={!c.n} onclick={() => store.go({ country: c.code, source: "" })}>
                <LevelDot tier={c.tier} size={10} /><span class="nm">{store.placeName(c.code)}</span><span class="n num">{c.n}</span>
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
  .overview { display: grid; gap: 18px; }
  header { display: grid; gap: 8px; }
  h1 { font-size: 22px; letter-spacing: -0.02em; line-height: 1.2; }
  .lead { font-size: 14px; color: var(--ink-2); line-height: 1.55; }
  .lead strong { color: var(--ink); font-weight: 600; }
  section { display: grid; gap: 6px; }
  h2 { font-size: 13px; font-weight: 600; color: var(--ink-2); display: flex; gap: 6px; align-items: baseline; }
  h2 .num { font-weight: 400; color: var(--ink-3); }
  ul { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 12px; }
  li button { display: grid; grid-template-columns: 10px 1fr auto; align-items: center; gap: 8px; width: 100%;
    padding: 5px 6px; border: 0; background: none; text-align: left; border-radius: var(--radius-sm); font-size: 13.5px; }
  li button:hover { background: var(--surface-3); }
  li button.zero { color: var(--ink-3); }
  .nm { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .n { font-size: 12px; color: var(--ink-3); }
  .cards { display: grid; gap: 8px; }
  .more { height: 36px; border: 1px solid var(--line-strong); border-radius: var(--radius); background: var(--surface); font-weight: 500; }
  .hint, .empty { font-size: 12.5px; color: var(--ink-3); }
</style>
