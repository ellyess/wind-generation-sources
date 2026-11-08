<script lang="ts">
  import { scaleLog } from "d3-scale";
  import { store } from "../store.svelte";
  import { BAND_TEXT, BAND_TONE, stepText, twh } from "../text";
  import Ext from "./Ext.svelte";

  let agr = $derived(store.checks.agreement);
  let links = $derived(store.checks.links);
  let snips = $derived(Object.values(store.checks.snippets ?? {}));
  let w = $state(700);
  let hover = $state<{ x: number; y: number; lines: string[] } | null>(null);
  const LO = 0.05, HI = 8;
  const PAD = 16, TOP = 22;
  // Narrow screens get a slimmer label column and fewer ticks, so the marks keep most of the width.
  let narrow = $derived(w < 560);
  let LABEL = $derived(narrow ? 104 : 150);
  let x = $derived(scaleLog().domain([LO, HI]).range([LABEL, Math.max(LABEL + 160, w - PAD)]).clamp(true));

  let rows = $derived.by(() => {
    if (!agr) return [];
    return Object.entries(agr.countries).map(([iso, c]) => {
      const ref = c.values.find((v) => v.source === c.reference.source)!;
      const vals = c.values.filter((v) => v.source !== c.reference.source && v.ratio != null);
      const worst = Math.max(0, ...vals.filter((v) => v.band !== "small").map((v) => Math.abs(Math.log(v.ratio!))));
      return { iso, ref: c.reference.name, refTwh: ref?.twh ?? 0, vals, worst };
    }).filter((r) => r.vals.length && r.refTwh > 0)
      .sort((a, b) => b.worst - a.worst || store.placeName(a.iso).localeCompare(store.placeName(b.iso)));
  });
  let judged = $derived(rows.flatMap((r) => r.vals).filter((v) => v.band && v.band !== "small"));
  let counts = $derived(["agrees", "noted", "outside"].map((b) => judged.filter((v) => v.band === b).length));
  // Taller rows on touch screens, so each country label is a 24px or larger target.
  const ROW = matchMedia("(pointer: coarse)").matches ? 28 : 22;
  let ticks = $derived(narrow ? [0.1, 0.5, 1, 2, 4] : [0.1, 0.25, 0.5, 0.7, 1, 1.3, 2, 4]);
  let H = $derived(rows.length * ROW);
  const short = (name: string) => (narrow && name.length > 15 ? `${name.slice(0, 14).trimEnd()}…` : name);
  let broken = $derived(links ? Object.entries(links.entries).flatMap(([id, r]) => r.broken.map((b) => ({ id, ...b }))) : []);
  let stepsOff = $derived(agr?.steps.filter((s) => !s.agrees) ?? []);
  let natRefs = $derived(agr ? Object.entries(agr.countries).filter(([, c]) => c.reference.kind.startsWith("national"))
    .sort(([a], [b]) => store.placeName(a).localeCompare(store.placeName(b))) : []);
</script>

<div class="checks">
  <header>
    <h1>Checks</h1>
    <p class="lead">By machine, each week: every link is requested, every Python snippet run, and each keyless source's {agr?.year ?? "annual"} wind total compared with a reference.</p>
    <details class="method"><summary>Method</summary>
      The total is summed from the raw data. The reference is the national figure where one covers the whole wind fleet for the calendar year,
      otherwise Eurostat's gross production, or Ember's outside Eurostat's countries. A national figure is only as good as its publisher.
      Within 15% agrees; within 30% is noted.
    </details>
  </header>
  {#if !links && !agr && !snips.length}<p class="loading">Loading the checks.</p>{/if}

  <dl class="stats">
    {#if links}
      <div><dt>Links that load</dt><dd class="num">{links.summary.ok} <small>of {links.summary.ok + links.summary.broken + links.summary.recheck + links.summary.unchecked}</small></dd><dd class="sub">{links.summary.broken} broken{links.summary.recheck ? `, ${links.summary.recheck} now load, so their traps may be out of date` : ""}, {links.summary.unchecked} not judged: refused automated requests or timed out</dd></div>
    {/if}
    {#if snips.length}
      <div><dt>Python snippets that ran cleanly</dt><dd class="num">{snips.filter((r) => r.result === "ok").length} <small>of {snips.length}</small></dd><dd class="sub">{snips.filter((r) => r.result === "failed").length} failed, {snips.filter((r) => r.result === "skipped").length} not run automatically</dd></div>
    {/if}
    {#if agr}
      <div><dt>Annual totals within 15%</dt><dd class="num">{counts[0]} <small>of {judged.length}</small></dd><dd class="sub">{counts[1]} within 30%, {counts[2]} further out</dd></div>
      <div><dt>Countries compared</dt><dd class="num">{rows.length}</dd><dd class="sub">Totals compared {agr.checked}</dd></div>
    {/if}
  </dl>

  {#if agr}
    <section class="plot">
      <h2>Each source's {agr.year} total as a ratio of the reference</h2>
      <p class="sub">Furthest disagreement first; log scale, bands at 15% and 30%. A match may only mean shared upstream data.</p>
      {#if natRefs.length}
        <details class="method"><summary>National references ({natRefs.length})</summary>{#each natRefs as [iso, c], i (iso)}{i ? "; " : ""}{store.placeName(iso)}, {#if c.reference.url}<Ext href={c.reference.url} label={c.reference.name} />{:else}<button type="button" class="lnk" onclick={() => store.go({ view: "sources", source: c.reference.source })}>{c.reference.name}</button>{/if}{/each}. Elsewhere Eurostat, or Ember outside Eurostat's countries.</details>
      {/if}
      <div class="legend">
        {#each ["agrees", "noted", "outside", "small"] as b (b)}
          {@const tone = BAND_TONE[b]}
          <span><svg class="mk t-{tone}" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
            {#if tone === "good"}<circle cx="6" cy="6" r="5" />{:else if tone === "warn"}<path d="M6 0.5 11.5 10.5H.5z" />{:else if tone === "bad"}<rect x="1.5" y="1.5" width="9" height="9" rx="1" />{:else}<circle class="ring" cx="6" cy="6" r="4" />{/if}
          </svg>{BAND_TEXT[b]}</span>
        {/each}
        <span><svg class="mk t-bad" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M10 1 3 6l7 5z" /></svg>Off the scale</span>
      </div>
      <div class="svgwrap" bind:clientWidth={w}>
        <svg width={w} height={H + TOP + 28} role="img" aria-label="Cross-check of annual wind totals for {rows.length} countries" onpointerleave={() => (hover = null)}>
          <g transform="translate(0,{TOP})">
          <rect class="b30" x={x(0.7)} y="0" width={x(1.3) - x(0.7)} height={H} />
          <rect class="b15" x={x(0.85)} y="0" width={x(1.15) - x(0.85)} height={H} />
          <!-- Ticks top and bottom, so the scale is readable wherever the long plot is scrolled to. -->
          <text class="ax cap" x={LABEL - 10} y="-8" text-anchor="end">Ratio</text>
          {#each ticks as t (t)}
            <line class={t === 1 ? "one" : "grid"} x1={x(t)} x2={x(t)} y1="0" y2={H} />
            <text class="ax" x={x(t)} y="-8" text-anchor="middle">{t}</text>
            <text class="ax" x={x(t)} y={H + 16} text-anchor="middle">{t}</text>
          {/each}
          {#each rows as r, i (r.iso)}
            <g transform="translate(0,{i * ROW})">
              <line class="row" x1={LABEL} x2={w - PAD} y1={ROW / 2} y2={ROW / 2} />
              <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
              <rect class="hit" x="0" y="0" width={LABEL} height={ROW} aria-hidden="true"
                onclick={() => store.go({ view: "map", country: r.iso, source: "" })} />
              <text class="cn" x={LABEL - 10} y={ROW / 2} dy="0.32em" text-anchor="end" role="button" tabindex="0"
                onclick={() => store.go({ view: "map", country: r.iso, source: "" })}
                onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); store.go({ view: "map", country: r.iso, source: "" }); } }}><title>{store.placeName(r.iso)}</title>{short(store.placeName(r.iso))}</text>
              {#each r.vals as v (v.source)}
                {@const s = store.byId.get(v.source)}
                {@const tone = BAND_TONE[v.band ?? "small"]}
                {@const off = v.ratio! < LO ? -1 : v.ratio! > HI ? 1 : 0}
                {@const cx = x(v.ratio!)}
                {@const cy = ROW / 2}
                <g class="mk t-{tone}" role="button" tabindex="-1"
                  onpointerenter={(e) => (hover = { x: Math.max(0, Math.min(e.offsetX, w - Math.min(300, w) - 16)), y: e.offsetY, lines: [`${store.placeName(r.iso)}: ${s ? `${s.publisher} · ${stepText(s)}` : v.publisher ?? v.source}`, `${twh(v.twh)} TWh against ${r.ref}'s ${twh(r.refTwh)} TWh`, `Ratio ${v.ratio!.toFixed(2)}, ${BAND_TEXT[v.band ?? "small"].toLowerCase()}`, ...(off ? [`Off the scale: drawn at the ${off < 0 ? "left" : "right"} edge`] : [])] })}
                  onclick={() => (s ? store.go({ view: "sources", source: v.source }) : v.url && window.open(v.url, "_blank", "noopener"))} onkeydown={() => {}}>
                  {#if off}
                    <path d={off < 0 ? `M${cx + 5},${cy - 6}L${cx - 3},${cy}L${cx + 5},${cy + 6}Z` : `M${cx - 5},${cy - 6}L${cx + 3},${cy}L${cx - 5},${cy + 6}Z`} />
                    <text class="edge" x={cx + (off < 0 ? 9 : -9)} y={cy} dy="0.32em" text-anchor={off < 0 ? "start" : "end"}>{off < 0 ? `<${LO}` : `>${HI}`}</text>
                  {:else if tone === "good"}<circle {cx} {cy} r="5" />
                  {:else if tone === "warn"}<path d="M{cx},{cy - 6}L{cx + 6},{cy + 4.5}L{cx - 6},{cy + 4.5}Z" />
                  {:else if tone === "bad"}<rect x={cx - 4.5} y={cy - 4.5} width="9" height="9" rx="1" />
                  {:else}<circle class="ring" {cx} {cy} r="4" />{/if}
                </g>
              {/each}
            </g>
          {/each}
          </g>
        </svg>
        {#if hover}
          <div class="tip" style:left="{hover.x}px" style:top="{hover.y}px">{#each hover.lines as l, i (i)}<span class:b={i === 0}>{l}</span>{/each}</div>
        {/if}
      </div>
      <details class="method astable"><summary>Show as a table</summary>
        <div class="tblwrap">
          <table>
            <thead><tr><th scope="col">Country</th><th scope="col">Source</th><th scope="col" class="r">TWh</th><th scope="col" class="r">Reference</th><th scope="col" class="r">Ratio</th><th scope="col">Band</th></tr></thead>
            <tbody>
              {#each rows as r (r.iso)}
                {#each r.vals as v (v.source)}
                  {@const s = store.byId.get(v.source)}
                  <tr><td>{store.placeName(r.iso)}</td>
                    <td>{#if s}<button type="button" class="lnk" onclick={() => store.go({ view: "sources", source: v.source })}>{s.publisher}</button> <span class="sub">{stepText(s)}</span>{:else}{v.publisher ?? v.source}{/if}</td>
                    <td class="r num">{twh(v.twh)}</td><td class="r num">{twh(r.refTwh)} <span class="sub">{r.ref}</span></td>
                    <td class="r num">{v.ratio!.toFixed(2)}</td><td>{BAND_TEXT[v.band ?? "small"]}</td></tr>
                {/each}
              {/each}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  {/if}

  {#if stepsOff.length || broken.length}
    <section class="issues">
      <h2>Needs a look</h2>
      <ul>
        {#each stepsOff as s (s.source)}<li><button type="button" onclick={() => store.go({ view: "sources", source: s.source })}>{store.byId.get(s.source)?.name ?? s.source}</button>: states {s.stated_minutes} minutes, the data show {s.observed_minutes}.</li>{/each}
        {#each broken as b (b.url)}<li><button type="button" onclick={() => store.go({ view: "sources", source: b.id })}>{store.byId.get(b.id)?.name ?? b.id}</button>: {b.role} link broken, <Ext href={b.url} />.</li>{/each}
      </ul>
    </section>
  {/if}
  <p class="sub">Full results: <a href="./data/checks.json">checks.json</a> · runs weekly on GitHub Actions</p>
</div>

<style>
  .hit { fill: transparent; cursor: pointer; }
  .checks { overflow-y: auto; height: 100%; padding: 28px 28px 56px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 22px; align-content: start; max-width: 1180px; margin: 0 auto; width: 100%; }
  header { display: grid; gap: 8px; }
  h1 { font-size: 24px; letter-spacing: -0.02em; }
  h2 { font-size: 15px; }
  .lead { color: var(--ink-2); max-width: 64ch; }
  .loading { color: var(--ink-3); font-size: 13.5px; }
  .astable .tblwrap { margin-top: 8px; max-height: 420px; overflow: auto; border: 1px solid var(--line); border-radius: var(--radius); }
  .astable table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  .astable th, .astable td { padding: 5px 8px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }
  .astable thead th { position: sticky; top: 0; background: var(--surface); color: var(--ink-2); font-weight: 600; }
  .astable .r { text-align: right; white-space: nowrap; }
  header :global(details.method) { max-width: 64ch; font-size: 12.5px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 0; }
  .stats div { padding: 14px 16px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
  .stats dt { font-size: 12.5px; color: var(--ink-2); }
  .stats dd { margin: 2px 0 0; }
  .stats dd.num { font-size: 26px; font-weight: 600; letter-spacing: -0.02em; }
  .stats small { font-size: 14px; font-weight: 400; color: var(--ink-3); }
  .sub { font-size: 12.5px; color: var(--ink-3); }
  .plot { display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; padding: 18px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12.5px; color: var(--ink-2); }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }

  .svgwrap { position: relative; min-width: 0; }
  svg { display: block; overflow: visible; }
  .b30 { fill: color-mix(in srgb, var(--warn-dot) 14%, transparent); }
  .b15 { fill: color-mix(in srgb, var(--good-dot) 13%, transparent); }
  .grid { stroke: var(--line); }
  .one { stroke: var(--ink-3); }
  .row { stroke: var(--line); stroke-dasharray: 1 3; }
  .ax { fill: var(--ink-3); font-size: 11px; font-variant-numeric: tabular-nums; }
  .ax.cap { font-weight: 500; }
  .cn { fill: var(--ink); font-size: 12.5px; cursor: pointer; }
  .cn:hover { fill: var(--accent-ink); text-decoration: underline; }
  g.mk { cursor: pointer; }
  g.mk > :not(text) { stroke: var(--surface); stroke-width: 1.5; }
  .t-good { fill: var(--good-dot); }
  .t-warn { fill: var(--warn-dot); }
  .t-bad { fill: var(--bad-dot); }
  .t-none { fill: var(--none-dot); }
  .mk .ring, svg.mk .ring { fill: none; stroke: var(--none-dot) !important; stroke-width: 1.6 !important; }
  .edge { fill: var(--ink-2); font-size: 10.5px; stroke: none !important; font-variant-numeric: tabular-nums; }
  .tip { position: absolute; z-index: 3; transform: translate(12px, 12px); pointer-events: none; display: grid; gap: 1px; padding: 8px 10px;
    background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow-2); font-size: 12.5px; color: var(--ink-2); max-width: min(300px, calc(100% - 8px)); }
  .tip .b { color: var(--ink); font-weight: 600; }
  .lnk { border: 0; background: none; padding: 0; font: inherit; color: var(--accent-ink); text-decoration: underline; text-underline-offset: 0.18em; }
  .issues ul { margin: 8px 0 0; padding-left: 18px; display: grid; gap: 4px; font-size: 13.5px; }
  .issues button { border: 0; background: none; padding: 0; color: var(--accent-ink); text-decoration: underline; font-weight: 500; }
  @media (max-width: 819px) {
    .checks { padding: 18px 16px 48px; }
    .plot { padding: 14px 12px; }
    .cn { font-size: 12px; }
    .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .stats div { padding: 12px; }
  }
</style>
