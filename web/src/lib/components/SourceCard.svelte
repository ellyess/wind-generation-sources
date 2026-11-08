<script lang="ts">
  import { hasLive } from "../live";
  import { store, type Indexed } from "../store.svelte";
  import { TEXT, coverageText, plural } from "../text";
  import Icon from "./Icon.svelte";
  import LevelDot from "./LevelDot.svelte";
  import Verdict from "./Verdict.svelte";

  let { s }: { s: Indexed } = $props();
  let traps = $derived((s.traps ?? []).length);
  let area = $derived(s.countries.length <= 3 ? s.countries.map(store.placeName).join(", ") : plural(s.countries.length, "country", "countries"));
</script>

<button type="button" class="card" onclick={() => store.go({ source: s.id })}>
  <span class="name">{s.name}</span>
  <span class="pub">{s.publisher}{store.country ? "" : ` · ${area}`}</span>
  <span class="top">
    <LevelDot tier={s._tier} size={10} />
    <span class="lvl">{TEXT.level[s.level]} · {TEXT.step[s.resolution]} · <span class="num">{coverageText(s.coverage)}</span></span>
    {#if hasLive(s.id)}<span class="tag live"><Icon name="live" size={12} />Live</span>{/if}
    {#if s.status !== "active"}<span class="tag">{TEXT.status[s.status]}</span>{/if}
    {#if s.reviewed !== false}<span class="tag rev" title="A person has checked this entry against the publisher's pages"><Icon name="check" size={11} />Reviewed</span>{/if}
  </span>
  <span class="foot">
    <Verdict value={s.licence.redistribution} />
    {#if traps}<span class="traps"><Icon name="trap" size={13} />{plural(traps, "trap")}</span>{/if}
    {#if s.access.key_required}<span class="key">Key needed</span>{/if}
  </span>
</button>

<style>
  .card {
    display: grid; gap: 3px; width: 100%; padding: 11px 12px 10px; text-align: left;
    background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
    transition: border-color 120ms ease, box-shadow 120ms ease;
  }
  .card:hover { border-color: var(--line-strong); box-shadow: var(--shadow-1); }
  .top { margin-top: 3px; display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; font-size: 12px; color: var(--ink-2); }
  .name { font-size: 14px; font-weight: 600; line-height: 1.35; color: var(--ink);
    display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .pub { font-size: 12.5px; color: var(--ink-2); }
  .foot { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 14px; margin-top: 2px; font-size: 12.5px; color: var(--ink-2); }
  .traps { display: inline-flex; align-items: center; gap: 4px; color: var(--ink); font-weight: 500; }
  .key { color: var(--ink-3); }
  .tag { display: inline-flex; align-items: center; gap: 3px; padding: 0 6px; height: 18px; border-radius: 9px;
    background: var(--surface-3); font-size: 11px; font-weight: 500; color: var(--ink-2); }
  .tag.live { background: var(--accent-wash); color: var(--accent-ink); }
  .tag.rev { gap: 3px; background: none; border: 1px solid var(--line-strong); color: var(--ink-2); }
</style>
