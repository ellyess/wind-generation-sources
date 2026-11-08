<script lang="ts">
  import { hasLive } from "../live";
  import { LEVELS, store } from "../store.svelte";
  import { STEPS, TIER, TIER_LONG, plural } from "../text";
  import AgreementStrip from "./AgreementStrip.svelte";
  import AnnualChart from "./AnnualChart.svelte";
  import CoverageChart from "./CoverageChart.svelte";
  import FarmTable from "./FarmTable.svelte";
  import LevelDot from "./LevelDot.svelte";
  import LiveChart from "./LiveChart.svelte";
  import SourceCard from "./SourceCard.svelte";
  import { TEXT } from "../text";

  let { code }: { code: string } = $props();
  // Finest level first; within a level, sources still running and open for use come before
  // finished, restricted or closed ones, so the first card is the best starting point.
  const NOW = new Date().getFullYear();
  type O = { level: string; resolution: string; status: string; coverage: { start: number; end?: number }; licence: { redistribution: string } };
  const running = (x: O) => (x.coverage.end == null || x.coverage.end >= NOW - 1 ? 0 : 1);
  const usable = (x: O) => (x.status === "active" ? 0 : 1) + (x.licence.redistribution === "prohibited" ? 1 : 0);
  const order = (a: O, b: O) =>
    (TIER[a.level] ?? 4) - (TIER[b.level] ?? 4) || running(a) - running(b) || usable(a) - usable(b)
    || LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level) || STEPS.indexOf(a.resolution) - STEPS.indexOf(b.resolution)
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
  // The best starting point: the first source in that order.
  let best = $derived(all[0]);
  const FEW = 5;
  let showAll = $state(false);
  let listed = $derived(showAll ? shown : shown.slice(0, FEW));
</script>

<div class="country">
  <nav class="crumbs" aria-label="Breadcrumb">
    <button type="button" onclick={() => store.go({ country: "", source: "" })}>World</button>
    <span aria-hidden="true">/</span>
    <button type="button" onclick={() => { store.set("region", continent); store.go({ country: "", source: "" }); }}>{continent}</button>
  </nav>
  <h1>{store.placeName(code)}</h1>
  <p class="sum">
    {plural(all.length, "source")} catalogued, {own.length} of them for {store.placeName(code)} alone.
    The finest is <LevelDot tier={finest} size={10} /> <strong>{TIER_LONG[finest].toLowerCase()}</strong>{#if best}, from {best.publisher}
    (re-hosting: {TEXT.reuse[best.licence.redistribution]?.toLowerCase()}{best.access.key_required ? ", key needed" : ""}){/if}.
    The earliest record starts in <span class="num">{earliest}</span>; {open ? `${open} of ${all.length} may be re-hosted` : "none may be re-hosted as they stand"}.
  </p>
  {#if checked}<p class="upd">Entries last checked <time datetime={checked}>{checked}</time>{store.checks.links ? `; links checked by machine ${store.checks.links.checked}` : ""}.</p>{/if}

  <h2>Sources {#if shown.length !== all.length}<span class="sub">{shown.length} of {all.length} under the filters</span>{/if}</h2>
  <div class="cards">
    {#each listed as s (s.id)}<SourceCard {s} />{/each}
    {#if shown.length > FEW}<button type="button" class="more" onclick={() => (showAll = !showAll)} aria-expanded={showAll}>{showAll ? "Show fewer" : `Show all ${shown.length} sources`}</button>{/if}
    {#if !shown.length}<p class="empty">No source for {store.placeName(code)} matches these filters. <button type="button" onclick={() => store.clearFilters()}>Clear filters</button></p>{/if}
  </div>

  <h2>Output and coverage</h2>
  {#if live}
    <div class="block"><LiveChart id={live.id} compact /></div>
  {/if}
  {#if eurostat}
    <div class="block"><AnnualChart {code} /></div>
  {/if}
  <div class="block"><CoverageChart list={all} /></div>
  <div class="block"><AgreementStrip {code} /></div>

  <FarmTable rows={farmRows} showSource={farmSources > 1} />
</div>

<style>
  .country { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; }
  .crumbs { display: flex; gap: 6px; align-items: center; font-size: 12.5px; color: var(--ink-3); }
  .crumbs button { border: 0; background: none; padding: 0; color: var(--accent-ink); }
  .crumbs button:hover { text-decoration: underline; }
  h1 { font-size: 26px; letter-spacing: -0.02em; }
  .sum { font-size: 14px; color: var(--ink-2); line-height: 1.55; }
  .sum strong { color: var(--ink); font-weight: 600; }
  .upd { margin-top: -6px; font-size: 12.5px; color: var(--ink-3); }
  .block { padding: 14px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
  h2 { font-size: 15px; margin-top: 10px; display: flex; gap: 8px; align-items: baseline; }
  .more { height: 34px; border: 1px solid var(--line-strong); border-radius: var(--radius); background: var(--surface); font-weight: 500; font-size: 13px; color: var(--ink-2); }
  .more:hover { color: var(--ink); border-color: var(--ink-3); }
  .sub { font-size: 12.5px; font-weight: 400; color: var(--ink-3); }
  .cards { display: grid; gap: 8px; }
  .empty { font-size: 13px; color: var(--ink-2); }
  .empty button { border: 0; background: none; color: var(--accent-ink); text-decoration: underline; padding: 0; }
</style>
