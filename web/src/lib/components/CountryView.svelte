<script lang="ts">
  import { hasLive } from "../live";
  import { LEVELS, store } from "../store.svelte";
  import { STEPS, TIER_LONG, plural } from "../text";
  import AgreementStrip from "./AgreementStrip.svelte";
  import AnnualChart from "./AnnualChart.svelte";
  import CoverageChart from "./CoverageChart.svelte";
  import FarmTable from "./FarmTable.svelte";
  import LevelDot from "./LevelDot.svelte";
  import LiveChart from "./LiveChart.svelte";
  import SourceCard from "./SourceCard.svelte";

  let { code }: { code: string } = $props();
  const order = (a: { level: string; resolution: string; coverage: { start: number } }, b: typeof a) =>
    LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level) || STEPS.indexOf(a.resolution) - STEPS.indexOf(b.resolution)
    || a.coverage.start - b.coverage.start;
  let all = $derived(store.sources.filter((s) => s.countries.includes(code)).sort(order));
  let shown = $derived(store.shown.slice().sort(order));
  let own = $derived(all.filter((s) => s.countries.length === 1));
  let finest = $derived(Math.min(...all.map((s) => s._tier)));
  let earliest = $derived(Math.min(...all.map((s) => s.coverage.start)));
  let open = $derived(all.filter((s) => ["allowed", "allowed-with-attribution"].includes(s.licence.redistribution)).length);
  let live = $derived(own.find((s) => hasLive(s.id)));
  let eurostat = $derived(store.byId.get("eu-eurostat-nrg-bal-peh")?.countries.includes(code) ?? false);
  let continent = $derived(store.continentOf(code));
  let checked = $derived(all.map((s) => s.last_checked).sort().at(-1));
  // Located farms in this country from the sources passing the filters.
  let farmRows = $derived.by(() => {
    const ok = new Set(shown.map((s) => s.id));
    const out: number[] = [];
    (store.farms?.farms ?? []).forEach((f, i) => { if (ok.has(f.entry) && store.farmCountry(f) === code) out.push(i); });
    return out;
  });
  let farmSources = $derived(new Set(farmRows.map((i) => store.farms!.farms[i].entry)).size);
</script>

<div class="country">
  <nav class="crumbs" aria-label="Breadcrumb">
    <button type="button" onclick={() => store.go({ country: "", source: "" })}>World</button>
    <span aria-hidden="true">/</span>
    <button type="button" onclick={() => { store.set("region", continent); store.go({ country: "", source: "" }); }}>{continent}</button>
  </nav>
  <h2>{store.placeName(code)}</h2>
  <p class="sum">
    {plural(all.length, "source")} catalogued, {own.length} of them for {store.placeName(code)} alone.
    The finest is <LevelDot tier={finest} size={10} /> <strong>{TIER_LONG[finest].toLowerCase()}</strong>; the earliest record starts in
    <span class="num">{earliest}</span>. {open ? `${open} may be re-hosted.` : "None may be re-hosted as they stand."}
  </p>
  {#if checked}<p class="upd">Entries last checked <time datetime={checked}>{checked}</time>{store.checks.links ? `; links checked by machine ${store.checks.links.checked}` : ""}.</p>{/if}

  {#if live}
    <div class="block"><LiveChart id={live.id} compact /></div>
  {/if}
  {#if eurostat}
    <div class="block"><AnnualChart {code} /></div>
  {/if}
  <div class="block"><CoverageChart list={all} /></div>
  <div class="block"><AgreementStrip {code} /></div>

  <h3>Sources {#if shown.length !== all.length}<span class="sub">{shown.length} of {all.length} under the filters</span>{/if}</h3>
  <div class="cards">
    {#each shown as s (s.id)}<SourceCard {s} />{/each}
    {#if !shown.length}<p class="empty">No source for {store.placeName(code)} matches these filters. <button type="button" onclick={() => store.clearFilters()}>Clear filters</button></p>{/if}
  </div>

  <FarmTable rows={farmRows} showSource={farmSources > 1} />
</div>

<style>
  .country { display: grid; gap: 14px; }
  .crumbs { display: flex; gap: 6px; align-items: center; font-size: 12.5px; color: var(--ink-3); }
  .crumbs button { border: 0; background: none; padding: 0; color: var(--accent-ink); }
  .crumbs button:hover { text-decoration: underline; }
  h2 { font-size: 26px; letter-spacing: -0.02em; }
  .sum { font-size: 14px; color: var(--ink-2); line-height: 1.55; }
  .sum strong { color: var(--ink); font-weight: 600; }
  .upd { margin-top: -6px; font-size: 12.5px; color: var(--ink-3); }
  .block { padding: 14px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
  h3 { font-size: 15px; margin-top: 6px; display: flex; gap: 8px; align-items: baseline; }
  .sub { font-size: 12.5px; font-weight: 400; color: var(--ink-3); }
  .cards { display: grid; gap: 8px; }
  .empty { font-size: 13px; color: var(--ink-2); }
  .empty button { border: 0; background: none; color: var(--accent-ink); text-decoration: underline; padding: 0; }
</style>
