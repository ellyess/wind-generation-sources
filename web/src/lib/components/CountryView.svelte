<script lang="ts">
  import { hasLive } from "../live";
  import { LEVELS, store } from "../store.svelte";
  import { STEPS, TIER, TIER_TEXT, coverageText, plural, shortName } from "../text";
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
  type O = { level: string; resolution: string; status: string; coverage: { start: number; end?: number };
    licence: { redistribution: string }; access: { key_required: boolean }; publisher_role?: string };
  const running = (x: O) => (x.coverage.end == null || x.coverage.end >= NOW - 1 ? 0 : 1);
  const REUSE_COST: Record<string, number> = {
    unclear: 1, "link-only": 1, "permission-required": 1, "non-commercial-only": 1, prohibited: 2,
  };
  // A fixed release is still there to download; only a stopped or closed source costs a point.
  const usable = (x: O) => (x.status === "active" || x.status === "fixed-release" ? 0 : 1) + (REUSE_COST[x.licence.redistribution] ?? 0)
    + (x.access.key_required ? 1 : 0);
  // A research dataset or one operator's own farms covers a site, not the country's fleet.
  const narrow = (x: O) => (x.publisher_role === "research" || x.publisher_role === "owner-operator" ? 1 : 0);
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
  // The cross-check strip draws only when the country has a reference total above zero.
  let agreed = $derived.by(() => {
    const c = store.checks.agreement?.countries[code];
    return !!c && c.values.some((v) => v.source === c.reference.source && v.twh > 0);
  });
  let checked = $derived(all.map((s) => s.last_checked).sort().at(-1));
  // Located farms in this country from the sources passing the filters.
  let farmRows = $derived.by(() => {
    const ok = new Set(shown.map((s) => s.id));
    const out: number[] = [];
    (store.farms?.farms ?? []).forEach((f, i) => { if (ok.has(f.entry) && store.farmCountry(f) === code) out.push(i); });
    return out;
  });
  let farmSources = $derived(new Set(farmRows.map((i) => store.farms!.farms[i].entry)).size);
  // The best starting point: a fleet-wide source before a single site, then the order above.
  // On a tie, a source for this country alone beats a world or regional one.
  const wide = (x: { countries: string[] }) => (x.countries.length === 1 ? 0 : 1);
  let best = $derived(all.slice().sort((a, b) => narrow(a) - narrow(b) || order(a, b) || wide(a) - wide(b))[0]);
  // The finest data may come from one research farm; say so rather than imply a national series.
  let finestIsSite = $derived(all.length > 0 && narrow(all[0]) === 1);

  // Ended sources close the range; any still running leaves it open.
  let latest = $derived(all.some((s) => s.coverage.end == null) ? undefined : Math.max(...all.map((s) => s.coverage.end ?? 0)));
  const FEW = 5;
  let showAll = $state(false);
  $effect(() => { void code; showAll = false; });
  let listed = $derived(showAll ? shown : shown.slice(0, FEW));
</script>

<div class="country">
  <nav class="crumbs" aria-label="Breadcrumb">
    <a {...store.link({ country: "", source: "" })}>World</a>
    <span aria-hidden="true">/</span>
    <button type="button" onclick={() => { store.set("region", continent); store.go({ country: "", source: "" }); }}>{continent}</button>
  </nav>
  <h1>{store.placeName(code)}</h1>
  <p class="sum">
    Finest data: <LevelDot tier={finest} size={10} /> <strong>{TIER_TEXT[finest].toLowerCase()}</strong>, {TEXT.step[all[0].resolution].toLowerCase()}{#if finestIsSite}{", from a single site "}({coverageText(all[0].coverage)}){/if}.
    {#if best}Start with <strong><a {...store.link({ source: best.id })} title={best.name}>{shortName(best.publisher)}</a></strong>{best !== all[0] ? ` (${TEXT.level[best.level].toLowerCase()}, ${TEXT.step[best.resolution].toLowerCase()})` : ""}:
      <span class="sub">re-hosting {TEXT.reuse[best.licence.redistribution]?.toLowerCase()}{best.access.key_required ? ", key needed" : ""}.</span>{/if}
  </p>
  <p class="upd num">
    <span>{plural(all.length, "source")}{own.length ? `, ${own.length} for ${store.placeName(code)} only` : all.length === 1 ? ", from a multi-country dataset" : ", all multi-country datasets"}</span>
    <span>Records {coverageText({ start: earliest, end: latest })}</span>
    <span>{open ? `${open} of ${all.length} may be re-hosted` : "none may be re-hosted"}</span>
    {#if checked}<span title="Entries last checked {checked}{store.checks.links ? `; links checked by machine ${store.checks.links.checked}` : ''}">Checked <time datetime={checked}>{checked}</time></span>{/if}
  </p>

  <h2>Sources {#if shown.length !== all.length}<span class="sub">{shown.length} of {all.length}, filtered</span>{/if}</h2>
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
  {#if agreed}<div class="block"><AgreementStrip {code} /></div>{/if}

  <FarmTable rows={farmRows} showSource={farmSources > 1} />
</div>

<style>
  .country { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; }
  .crumbs { display: flex; gap: 6px; align-items: center; font-size: 12.5px; color: var(--ink-3); }
  .crumbs a { text-decoration: none; }
  .crumbs button { border: 0; background: none; padding: 0; color: var(--accent-ink); }
  .crumbs a:hover, .crumbs button:hover { text-decoration: underline; }
  h1 { font-size: 26px; letter-spacing: -0.02em; }
  .sum { font-size: 14px; color: var(--ink-2); line-height: 1.55; }
  .sum strong { color: var(--ink); font-weight: 600; }
  .sum .sub { font-size: 13px; }
  .upd { margin-top: -8px; display: flex; flex-wrap: wrap; font-size: 12.5px; color: var(--ink-3); }
  .upd > :not(:last-child)::after { content: "·"; margin: 0 7px; }
  .block { padding: 14px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
  h2 { font-size: 15px; margin-top: 10px; display: flex; gap: 8px; align-items: baseline; }
  .more { height: 34px; border: 1px solid var(--line-strong); border-radius: var(--radius); background: var(--surface); font-weight: 500; font-size: 13px; color: var(--ink-2); }
  .more:hover { color: var(--ink); border-color: var(--ink-3); }
  .sub { font-size: 12.5px; font-weight: 400; color: var(--ink-3); }
  .cards { display: grid; gap: 8px; }
  .empty { font-size: 13px; color: var(--ink-2); }
  .empty button { border: 0; background: none; color: var(--accent-ink); text-decoration: underline; padding: 0; }
</style>
