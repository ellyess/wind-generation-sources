<script lang="ts">
  import { scaleBand, scaleLinear } from "d3-scale";
  import { fetchEurostat, type Annual, type AnnualPoint } from "../live";
  import { store } from "../store.svelte";
  import Ext from "./Ext.svelte";

  let { code }: { code: string } = $props();
  let data = $state<Annual | null>(null);
  let err = $state("");
  let w = $state(360);
  let hover = $state<number | null>(null);
  type Mode = "gen" | "cap" | "cf";
  let mode = $state<Mode>("gen");
  $effect(() => {
    const want = code;
    data = null; err = ""; hover = null;
    fetchEurostat(want).then((d) => { if (want === code) data = d; }).catch((e) => { if (want === code) err = e.message; });
  });

  const nf = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });
  const MODES: Record<Mode, { tab: string; title: string; get: (p: AnnualPoint) => number | undefined; fmt: (v: number) => string }> = {
    gen: { tab: "Generation", title: "Wind generation per year (TWh)", get: (p) => p.gwh / 1000, fmt: (v) => `${nf.format(v)} TWh` },
    cap: { tab: "Capacity", title: "Installed wind capacity at year end (GW)", get: (p) => (p.mw != null ? p.mw / 1000 : undefined), fmt: (v) => `${nf.format(v)} GW` },
    cf: { tab: "Capacity factor", title: "Capacity factor per year (%)", get: (p) => (p.cf != null ? p.cf * 100 : undefined), fmt: (v) => `${v.toFixed(1)}%` },
  };
  const H = 120, M = { t: 10, r: 4, b: 20, l: 40 };

  let all = $derived(data?.points.filter((p) => p.gwh > 0 || p.year >= 2000) ?? []);
  let hasCap = $derived(all.some((p) => p.mw != null));
  let hasCf = $derived(all.filter((p) => p.cf != null).length > 1);
  let m = $derived(MODES[mode]);
  let pts = $derived(all.filter((p) => m.get(p) != null));
  let x = $derived(scaleBand<number>().domain(pts.map((p) => p.year)).range([M.l, w - M.r]).padding(0.18));
  let y = $derived(scaleLinear().domain([0, Math.max(mode === "cf" ? 10 : 1, ...pts.map((p) => m.get(p) ?? 0))]).nice(3).range([H - M.b, M.t]));
  let hp = $derived(hover != null ? pts[hover] : pts[pts.length - 1]);
  $effect(() => { if ((mode === "cap" && !hasCap) || (mode === "cf" && !hasCf)) mode = "gen"; });
  const setMode = (k: Mode) => { mode = k; hover = null; };
  // A series that stops well short of the present (GB after Brexit) says so, rather than looking current.
  let stale = $derived.by(() => { const last = all.at(-1)?.year; return last && last < new Date().getFullYear() - 3 ? last : null; });
</script>

{#if !err && (data === null || all.length > 1)}
<figure class="annual">
  <figcaption>
    <span class="t">{m.title}, Eurostat</span>
    {#if hp}<span class="num">{hp.year}: <b>{m.fmt(m.get(hp) ?? 0)}</b></span>{/if}
  </figcaption>
  {#if data && (hasCap || hasCf)}
    <div class="tabs" role="group" aria-label="Annual series">
      {#each Object.entries(MODES) as [k, v] (k)}
        {#if k === "gen" || (k === "cap" && hasCap) || (k === "cf" && hasCf)}
          <button type="button" aria-pressed={mode === k} class:on={mode === k} onclick={() => setMode(k as Mode)}>{v.tab}</button>
        {/if}
      {/each}
    </div>
  {/if}
  <div bind:clientWidth={w}>
    {#if !data}
      <div class="skeleton" style:height="{H}px"></div>
    {:else if pts.length}
      <svg width={w} height={H} role="img" aria-label="{m.title} in {store.placeName(code)} from {pts[0].year} to {pts[pts.length - 1].year}"
        onpointerleave={() => (hover = null)}>
        {#each y.ticks(3) as t (t)}
          <line class="grid" x1={M.l} x2={w - M.r} y1={y(t)} y2={y(t)} />
          <text class="ax" x={M.l - 6} y={y(t)} dy="0.32em" text-anchor="end">{t}{mode === "cf" ? "%" : ""}</text>
        {/each}
        {#each pts as p, i (p.year)}
          {@const v = m.get(p) ?? 0}
          <rect class="bar" class:dim={hover != null && hover !== i} x={x(p.year)} y={y(v)} width={x.bandwidth()}
            height={Math.max(0, H - M.b - y(v))} rx="1.5" />
          <rect class="hit" x={(x(p.year) ?? 0) - 1} y={M.t} width={x.bandwidth() + 2} height={H - M.t - M.b}
            role="presentation" onpointerenter={() => (hover = i)} />
          {#if p.year % 10 === 0 || (i === 0 && p.year % 10 < 5)}
            <text class="ax" x={(x(p.year) ?? 0) + x.bandwidth() / 2} y={H - 5} text-anchor="middle">{p.year}</text>
          {/if}
        {/each}
      </svg>
    {/if}
  </div>
  {#if data}
    <p class="src">
      {#if mode === "gen"}Gross production, fetched live.{#if stale}{" "}Eurostat has no figure for {store.placeName(code)} after {stale}.{/if}
      {:else if mode === "cap"}Net maximum capacity at 31 December, fetched live.
      {:else}Reads slightly high: compare years with it, not as a fleet's true yield.{/if}
    </p>
    <details class="method"><summary>Method</summary>
      {#if mode === "gen"}Eurostat nrg_bal_peh, RA300. <Ext href={data.request} label="Raw request" />
      {:else if mode === "cap"}Eurostat nrg_inf_epcrw. <Ext href={data.capacityRequest} label="Raw request" />
      {:else}Gross generation divided by the mean of this and last year's year-end net capacity, times the hours in the year.
        Years when the fleet grew by more than half are left out. Gross over net is why it reads high.{/if}
    </details>
  {/if}
</figure>
{/if}

<style>
  .annual { margin: 0; display: grid; gap: 6px; }
  figcaption { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 12px; font-size: 13px; color: var(--ink-2); }
  .t { font-weight: 600; color: var(--ink); }
  b { color: var(--ink); font-weight: 600; }
  .tabs { display: inline-flex; gap: 2px; padding: 2px; border-radius: var(--radius-sm); background: var(--surface-3); justify-self: start; }
  .tabs button { border: 0; background: none; font: inherit; font-size: 12px; font-weight: 500; color: var(--ink-2);
    padding: 3px 10px; border-radius: calc(var(--radius-sm) - 2px); cursor: pointer; }
  .tabs button:hover { color: var(--ink); }
  .tabs button.on { background: var(--surface); color: var(--ink); box-shadow: 0 0 0 1px var(--line); }
  svg { display: block; }
  .grid { stroke: var(--line); }
  .ax { fill: var(--ink-3); font-size: 11px; font-variant-numeric: tabular-nums; }
  .bar { fill: var(--l3); }
  .bar.dim { opacity: 0.45; }
  .hit { fill: transparent; }
  .skeleton { border-radius: var(--radius-sm); background: var(--surface-3); }
  .src { font-size: 12px; color: var(--ink-3); }
</style>
