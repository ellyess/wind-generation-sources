<script lang="ts">
  import { store, type Indexed } from "../store.svelte";
  import { TEXT, coverageText } from "../text";

  // Years each source covers, one row each, coloured by its level as on the map.
  let { list }: { list: Indexed[] } = $props();
  const now = new Date().getFullYear();
  let y0 = $derived(Math.min(2000, ...list.map((s) => Math.floor(s.coverage.start / 5) * 5)));
  let span = $derived(now + 1 - y0);
  let ticks = $derived.by(() => {
    const step = span > 40 ? 10 : 5;
    const out: number[] = [];
    for (let y = Math.ceil(y0 / step) * step; y <= now; y += step) out.push(y);
    return out;
  });
  const pos = (y: number) => `${(((y - y0) / span) * 100).toFixed(3)}%`;
</script>

<figure class="cov">
  <figcaption><span class="t">Years covered</span><span class="n">Shaded by the finest level, as on the map</span></figcaption>
  <ol>
    {#each list as s (s.id)}
      {@const end = s.coverage.end ? s.coverage.end + 1 : now + 1}
      <li>
        <button type="button" class="nm" onclick={() => store.go({ source: s.id })} title={s.name}>
          <span class="pub">{s.publisher}</span>
          <span class="meta">{TEXT.level[s.level]} · {TEXT.step[s.resolution]}</span>
        </button>
        <span class="track" aria-hidden="true">
          {#each ticks as t (t)}<i class="tick" style:left={pos(t)}></i>{/each}
          <span class="bar" class:live={!s.coverage.end} class:ended={s.status !== "active"}
            style:left={pos(s.coverage.start)} style:width="calc({pos(end)} - {pos(s.coverage.start)})"
            style:--c="var(--l{s._tier})"></span>
        </span>
        <span class="visually-hidden">{coverageText(s.coverage)}</span>
        <span class="yrs num" aria-hidden="true">{coverageText(s.coverage)}</span>
      </li>
    {/each}
  </ol>
  <div class="axis" aria-hidden="true">
    <span class="ticks">{#each ticks as t (t)}<span style:left={pos(t)}>{t}</span>{/each}</span>
  </div>
</figure>

<style>
  .cov { margin: 0; display: grid; gap: 8px; }
  figcaption { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; font-size: 13px; }
  .t { font-weight: 600; }
  .n { color: var(--ink-3); font-size: 12px; }
  ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
  ol { gap: 6px; }
  li { display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "nm yrs" "track track"; align-items: end; gap: 2px 10px; }
  .axis { display: block; }
  .nm { grid-area: nm; display: flex; gap: 8px; align-items: baseline; text-align: left; border: 0; background: none; padding: 2px 4px; margin-left: -4px; border-radius: var(--radius-sm); min-width: 0; }
  .track { grid-area: track; }
  .yrs { grid-area: yrs; }
  .nm:hover { background: var(--surface-3); }
  .pub { font-size: 12.5px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
  .meta { flex: none; font-size: 11.5px; color: var(--ink-3); white-space: nowrap; }
  .track { position: relative; height: 10px; }
  .tick { position: absolute; top: -4px; bottom: -4px; width: 1px; background: var(--line); }
  .bar { position: absolute; top: 0; bottom: 0; background: var(--c); border-radius: 3px; min-width: 3px; }
  .bar.live { border-radius: 3px 0 0 3px; mask-image: linear-gradient(to right, #000 calc(100% - 10px), rgb(0 0 0 / 0.35)); }
  .bar.ended { opacity: 0.55; }
  .yrs { font-size: 11.5px; color: var(--ink-2); text-align: right; white-space: nowrap; }
  .axis { font-size: 11px; color: var(--ink-3); font-variant-numeric: tabular-nums; }
  .ticks { position: relative; display: block; height: 14px; }
  .ticks span { position: absolute; transform: translateX(-50%); }
</style>
