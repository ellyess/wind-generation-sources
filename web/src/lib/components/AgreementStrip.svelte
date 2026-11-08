<script lang="ts">
  import { store } from "../store.svelte";
  import { BAND_TEXT, BAND_TONE, stepText, twh } from "../text";
  import Ext from "./Ext.svelte";

  // Each source's annual wind total as a ratio of the reference, on one shared axis.
  let { code }: { code: string } = $props();
  const LO = 0.5, HI = 1.5;
  const pos = (r: number) => `${(((Math.min(Math.max(r, LO), HI) - LO) / (HI - LO)) * 100).toFixed(2)}%`;
  let agr = $derived(store.checks.agreement);
  let c = $derived(agr?.countries[code]);
  let ref = $derived(c?.values.find((v) => v.source === c!.reference.source));
  let national = $derived(c?.reference.kind.startsWith("national") ?? false);
</script>

{#if agr && c && ref && ref.twh > 0}
  <figure class="agree">
    <figcaption>
      <span class="t">Annual totals compared</span>
      <span class="n">{agr.year}, against {c.reference.publisher ?? c.reference.name}'s {twh(ref.twh)} TWh{national ? " (national figure)" : ""}. Bands: 15% and 30%.</span>
    </figcaption>
    <ol>
      {#each c.values as v (v.source)}
        {@const isRef = v.source === c.reference.source}
        {@const s = store.byId.get(v.source)}
        {@const tone = isRef ? "ref" : BAND_TONE[v.band ?? "small"]}
        <li>
          {#if s}<a class="nm" {...store.link({ source: v.source })} title="{s.publisher}, {stepText(s).toLowerCase()} data"><span class="pn">{s.publisher}</span><small>{stepText(s)}</small></a>
          {:else}<a class="nm" href={v.url} target="_blank" rel="noopener"><span class="pn">{v.publisher ?? v.source}</span><small>Annual figure</small></a>{/if}
          <span class="val num">{twh(v.twh)}&nbsp;<small>TWh</small></span>
          <span class="scale" role="img" aria-label={isRef ? "Reference" : `Ratio ${v.ratio?.toFixed(2)}, ${BAND_TEXT[v.band ?? "small"]}`}>
            <i class="b30"></i><i class="b15"></i><i class="one"></i>
            <b class="mk t-{tone}" class:clamped={v.ratio != null && (v.ratio < LO || v.ratio > HI)} style:left={pos(isRef ? 1 : v.ratio ?? 1)}></b>
          </span>
          <span class="ratio num">{isRef ? "Ref." : v.ratio?.toFixed(2) ?? "–"}</span>
        </li>
      {/each}
    </ol>
    <div class="axis" aria-hidden="true"><span></span><span></span>
      <span class="ticks">{#each [0.7, 1, 1.3] as m (m)}<span style:left={pos(m)}>{m === 1 ? "1" : m}</span>{/each}</span><span></span></div>
    <p class="cave">Catches series that miss part of the fleet. A match may only mean shared upstream data.</p>
    {#if national}<details class="method"><summary>Why this reference</summary>{c.reference.why}{#if c.reference.url} <Ext href={c.reference.url} label="Evidence" />{/if}</details>{/if}
  </figure>
{/if}

<style>
  .agree { margin: 0; display: grid; gap: 8px; container-type: inline-size; }
  figcaption { display: grid; gap: 2px; font-size: 13px; }
  .t { font-weight: 600; }
  .n, .cave { color: var(--ink-3); font-size: 12px; }
  ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
  li, .axis { display: grid; grid-template-columns: minmax(0, 8rem) 4.2rem 1fr 2.6rem; align-items: center; gap: 10px; }
  .nm { color: inherit; text-decoration: none; text-align: left; border: 0; background: none; padding: 2px 4px; margin-left: -4px; border-radius: var(--radius-sm);
    font-size: 12.5px; font-weight: 500; display: grid; min-width: 0; line-height: 1.25; }
  .nm .pn { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .nm:hover { background: var(--surface-3); }
  .nm small { font-size: 11px; font-weight: 400; color: var(--ink-3); }
  .val { font-size: 12.5px; text-align: right; }
  small { color: var(--ink-3); font-size: 11px; }
  .ratio { font-size: 12.5px; text-align: right; color: var(--ink-2); }
  .scale { position: relative; height: 16px; }
  .scale i { position: absolute; top: 0; bottom: 0; }
  .b30 { left: 20%; right: 20%; background: color-mix(in srgb, var(--warn-dot) 14%, transparent); }
  .b15 { left: 35%; right: 35%; background: color-mix(in srgb, var(--good-dot) 18%, transparent); }
  .one { left: 50%; width: 1px; background: var(--ink-3); }
  .mk { position: absolute; top: 50%; width: 10px; height: 10px; margin: -5px 0 0 -5px; border-radius: 50%;
    box-shadow: 0 0 0 2px var(--surface); }
  .mk.clamped { width: 8px; border-radius: 2px; }
  .t-good { background: var(--good-dot); }
  .t-warn { background: var(--warn-dot); border-radius: 0; clip-path: polygon(50% 0, 100% 100%, 0 100%); width: 12px; height: 11px; margin: -6px 0 0 -6px; }
  .t-bad { background: var(--bad-dot); border-radius: 1px; width: 9px; height: 9px; margin: -4.5px 0 0 -4.5px; }
  .t-none { background: transparent; box-shadow: inset 0 0 0 2px var(--none-dot); }
  .t-ref { background: var(--ink); }
  .axis { font-size: 11px; color: var(--ink-3); }
  .ticks { position: relative; height: 14px; }
  .ticks span { position: absolute; transform: translateX(-50%); font-variant-numeric: tabular-nums; }
  /* In a narrow panel or on a phone, give the scale room: shorter name and value columns. */
  @container (max-width: 380px) {
    li, .axis { grid-template-columns: minmax(0, 5.5rem) 3.4rem 1fr 2.2rem; gap: 6px; }
  }
</style>
