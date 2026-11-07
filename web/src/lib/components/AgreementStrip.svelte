<script lang="ts">
  import { store } from "../store.svelte";
  import { BAND_TEXT, BAND_TONE, REF_NAME, twh } from "../text";

  // Each source's annual wind total as a ratio of the reference, on one shared axis.
  let { code }: { code: string } = $props();
  const LO = 0.5, HI = 1.5;
  const pos = (r: number) => `${(((Math.min(Math.max(r, LO), HI) - LO) / (HI - LO)) * 100).toFixed(2)}%`;
  let agr = $derived(store.checks.agreement);
  let c = $derived(agr?.countries[code]);
  let ref = $derived(c?.values.find((v) => v.source === c!.reference));
</script>

{#if agr && c && ref && ref.twh > 0}
  <figure class="agree">
    <figcaption>
      <span class="t">Annual totals agree?</span>
      <span class="n">{agr.year}, each source against {REF_NAME[c.reference]}'s {twh(ref.twh)} TWh. Shaded: within 15% and 30%.</span>
    </figcaption>
    <ol>
      {#each c.values as v (v.source)}
        {@const isRef = v.source === c.reference}
        {@const s = store.byId.get(v.source)}
        {@const tone = isRef ? "ref" : BAND_TONE[v.band ?? "small"]}
        <li>
          <button type="button" class="nm" onclick={() => store.go({ source: v.source })}>{s?.publisher ?? v.source}</button>
          <span class="val num">{twh(v.twh)}<small> TWh</small></span>
          <span class="scale" role="img" aria-label={isRef ? "Reference" : `Ratio ${v.ratio?.toFixed(2)}, ${BAND_TEXT[v.band ?? "small"]}`}>
            <i class="b30"></i><i class="b15"></i><i class="one"></i>
            <b class="mk t-{tone}" class:clamped={v.ratio != null && (v.ratio < LO || v.ratio > HI)} style:left={pos(isRef ? 1 : v.ratio ?? 1)}></b>
          </span>
          <span class="ratio num">{isRef ? "Ref." : v.ratio?.toFixed(2) ?? "–"}</span>
        </li>
      {/each}
    </ol>
    <div class="axis" aria-hidden="true"><span></span><span></span>
      <span class="ticks">{#each [0.7, 1, 1.3] as m (m)}<span style:left={pos(m)}>{m.toFixed(2)}</span>{/each}</span><span></span></div>
    <p class="cave">A match can mean shared upstream data rather than independent confirmation. The check catches a series that covers only part of a fleet.</p>
  </figure>
{/if}

<style>
  .agree { margin: 0; display: grid; gap: 8px; }
  figcaption { display: grid; gap: 2px; font-size: 13px; }
  .t { font-weight: 600; }
  .n, .cave { color: var(--ink-3); font-size: 12px; }
  ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
  li, .axis { display: grid; grid-template-columns: minmax(0, 8rem) 4.2rem 1fr 2.6rem; align-items: center; gap: 10px; }
  .nm { text-align: left; border: 0; background: none; padding: 2px 4px; margin-left: -4px; border-radius: var(--radius-sm);
    font-size: 12.5px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .nm:hover { background: var(--surface-3); }
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
</style>
