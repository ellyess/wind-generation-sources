<script lang="ts">
  import { scaleLinear, scaleTime } from "d3-scale";
  import { area, line, curveMonotoneX } from "d3-shape";
  import { bisector } from "d3-array";
  import { timeFormat } from "d3-time-format";
  import { timeDay } from "d3-time";
  import { fetchLive, type Series } from "../live";
  import { store } from "../store.svelte";
  import Ext from "./Ext.svelte";
  import Icon from "./Icon.svelte";

  let { id, compact = false }: { id: string; compact?: boolean } = $props();
  let src = $derived(store.byId.get(id));
  let data = $state<Series | null>(null);
  let err = $state("");
  let w = $state(360);
  let hover = $state<number | null>(null);

  $effect(() => {
    const want = id;
    data = null; err = ""; hover = null;
    fetchLive(want).then((d) => { if (want === id) data = d; }).catch((e) => { if (want === id) err = e.message; });
  });

  const H = $derived(compact ? 132 : 168);
  const M = { t: 10, r: 8, b: 22, l: 40 };
  let x = $derived(data && data.points.length
    ? scaleTime().domain([data.points[0].t, data.points[data.points.length - 1].t]).range([M.l, w - M.r])
    : null);
  let y = $derived(data ? scaleLinear().domain([0, Math.max(1, ...data.points.map((p) => p.v))]).nice(4).range([H - M.b, M.t]) : null);
  let path = $derived(data && x && y && data.kind === "line"
    ? line<{ t: Date; v: number }>().x((p) => x!(p.t)).y((p) => y!(p.v)).curve(curveMonotoneX)(data.points) : "");
  let fill = $derived(data && x && y && data.kind === "line"
    ? area<{ t: Date; v: number }>().x((p) => x!(p.t)).y0(H - M.b).y1((p) => y!(p.v)).curve(curveMonotoneX)(data.points) : "");
  let barW = $derived(data && x && data.kind === "bars" && data.points.length > 1
    ? Math.max(2, (w - M.l - M.r) / data.points.length - 2) : 6);
  const fmtDay = timeFormat("%-d %b");
  // Daily ticks thinned by index, so they never bunch at a month boundary.
  let dayTicks = $derived.by(() => {
    if (!x) return [];
    const [a, b] = x.domain();
    const days = timeDay.range(timeDay.ceil(a), b);
    const every = Math.max(1, Math.ceil(days.length / Math.max(2, Math.floor(w / 80))));
    return days.filter((_, i) => i % every === 0);
  });
  const fmtTime = timeFormat("%-d %b %H:%M");
  const bis = bisector((p: { t: Date }) => p.t).center;
  const nf = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });

  function move(e: PointerEvent) {
    if (!data || !x) return;
    const r = (e.currentTarget as SVGElement).getBoundingClientRect();
    hover = bis(data.points, x.invert(e.clientX - r.left));
  }
  let hp = $derived(hover != null && data ? data.points[hover] : null);
  let peak = $derived(data && data.points.length ? data.points.reduce((a, b) => (b.v > a.v ? b : a)) : null);
  let last = $derived(data && data.points.length ? data.points[data.points.length - 1] : null);
</script>

<figure class="live" class:compact>
  <figcaption>
    <span class="t"><Icon name="live" />{data?.kind === "bars" ? "Last 30 days" : "Last 7 days"}, live from {src?.publisher ?? "the publisher"}</span>
    {#if last && data}
      <span class="read num">{hp ? (data.kind === "bars" ? fmtDay(hp.t) : fmtTime(hp.t)) : "Latest"}: <b>{nf.format((hp ?? last).v)} {data.unit}</b><span class="u"> · axis in {data.unit}</span></span>
    {/if}
  </figcaption>

  <div class="plot" bind:clientWidth={w}>
    {#if err}
      <p class="state">The publisher did not answer this request ({err}). It may be busy or rate limited; the source itself is unaffected.</p>
    {:else if !data || !x || !y}
      <div class="skeleton" style:height="{H}px" aria-label="Loading live data"></div>
    {:else if !data.points.length}
      <p class="state">The publisher returned no values for this window.</p>
    {:else}
      <svg width={w} height={H} role="img" aria-label="{src?.name}: {data.unit === 'MW' ? 'wind output' : 'daily wind energy'}, peak {nf.format(peak!.v)} {data.unit}"
        onpointermove={move} onpointerleave={() => (hover = null)}>
        {#each y.ticks(4) as t (t)}
          <line class="grid" x1={M.l} x2={w - M.r} y1={y(t)} y2={y(t)} />
          <text class="ax" x={M.l - 6} y={y(t)} dy="0.32em" text-anchor="end">{t >= 1000 ? `${t / 1000}k` : t}</text>
        {/each}
        {#each dayTicks as t (+t)}
          <text class="ax" x={x(t)} y={H - 6} text-anchor="middle">{fmtDay(t)}</text>
        {/each}
        {#if data.kind === "line"}
          <path class="area" d={fill} />
          <path class="line" d={path} />
        {:else}
          {#each data.points as p, i (i)}
            <rect class="bar" class:dim={hover != null && hover !== i} x={x(p.t) - barW / 2} y={y(p.v)} width={barW}
              height={Math.max(0, H - M.b - y(p.v))} rx="2" />
          {/each}
        {/if}
        {#if hp && data.kind === "line"}
          <line class="cross" x1={x(hp.t)} x2={x(hp.t)} y1={M.t} y2={H - M.b} />
          <circle class="pt" cx={x(hp.t)} cy={y(hp.v)} r="4" />
        {/if}
      </svg>
    {/if}
  </div>

  {#if data}
    <p class="src">
      Fetched by your browser just now, {data.stepText} values; nothing is stored here.
      {data.note ?? ""}
      <Ext href={data.request} label="Raw request" />
      {#if src?.licence.attribution}<span class="cred">{src.licence.attribution}</span>{/if}
    </p>
  {/if}
</figure>

<style>
  .live { margin: 0; display: grid; gap: 6px; }
  figcaption { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 12px; font-size: 13px; color: var(--ink-2); }
  .t { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; color: var(--ink); }
  .t :global(.ic) { color: var(--accent); }
  .read b { color: var(--ink); font-weight: 600; }
  .u { color: var(--ink-3); }
  .plot { min-height: 40px; }
  svg { display: block; touch-action: pan-y; }
  .grid { stroke: var(--line); stroke-width: 1; }
  .ax { fill: var(--ink-3); font-size: 11px; font-variant-numeric: tabular-nums; }
  .line { fill: none; stroke: var(--l2); stroke-width: 2; stroke-linejoin: round; }
  .area { fill: var(--l2); opacity: 0.12; }
  .bar { fill: var(--l2); }
  .bar.dim { opacity: 0.45; }
  .cross { stroke: var(--ink-3); stroke-width: 1; stroke-dasharray: 2 3; }
  .pt { fill: var(--l2); stroke: var(--surface); stroke-width: 2; }
  .skeleton { border-radius: var(--radius-sm); background: linear-gradient(90deg, var(--surface-3), var(--surface-2), var(--surface-3));
    background-size: 200% 100%; animation: shimmer 1.4s ease-in-out infinite; }
  @keyframes shimmer { to { background-position: -200% 0; } }
  .state { padding: 12px; background: var(--surface-2); border-radius: var(--radius-sm); font-size: 13px; color: var(--ink-2); }
  .src { font-size: 12px; color: var(--ink-3); line-height: 1.45; }
  .cred { display: block; margin-top: 2px; font-style: italic; }
</style>
