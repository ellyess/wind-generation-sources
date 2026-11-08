<script lang="ts">
  import { CONTINENTS, LEVELS, store } from "../store.svelte";
  import { TEXT, TIER_TEXT } from "../text";
  import Icon from "./Icon.svelte";
  // Each search re-filters the map and lists, so wait for a pause in typing.
  let typing: ReturnType<typeof setTimeout> | undefined;
  const typed = (v: string) => { clearTimeout(typing); typing = setTimeout(() => store.set("q", v), v ? 150 : 0); };

  let { wide = false }: { wide?: boolean } = $props();
  let levels = $derived(LEVELS.filter((l) => store.sources.some((s) => s.level === l)));
  let n = $derived(store.country ? store.shown.length : store.filtered.length);
  // On phones the menus fold behind one button, so the list starts near the top of the screen.
  let open = $state(false);
  let picked = $derived(store.activeFilters - (store.q ? 1 : 0));
  let total = $derived(store.country ? store.sources.filter((s) => s.countries.includes(store.country)).length : store.sources.length);
</script>

<div class="filters" class:wide role="search" aria-label="Filter sources">
  <label class="search">
    <Icon name="search" />
    <span class="visually-hidden">Search</span>
    <input type="search" placeholder="Search country, publisher, dataset or trap" autocomplete="off" spellcheck="false"
      value={store.q} oninput={(e) => typed(e.currentTarget.value)} />
  </label>
  <button type="button" class="ftoggle" aria-expanded={open} aria-controls="filter-menus" onclick={() => (open = !open)}>
    <Icon name="chev" size={14} />Filters{picked ? ` · ${picked}` : ""}
  </button>
  <div class="sel" id="filter-menus" class:open>
    <label><span>Region</span>
      <select value={store.region} onchange={(e) => store.set("region", e.currentTarget.value)}>
        <option value="">Anywhere</option>
        {#each CONTINENTS as c (c)}<option value={c}>{c}</option>{/each}
      </select></label>
    <label><span>Level</span>
      <select value={store.level} onchange={(e) => store.set("level", e.currentTarget.value)}>
        <option value="">Any level</option>
        <optgroup label="Map groups">{#each [1, 2, 3, 4] as t (t)}<option value="tier:{t}">{TIER_TEXT[t]}</option>{/each}</optgroup>
        <optgroup label="Exact level">{#each levels as l (l)}<option value={l}>{TEXT.level[l]} only</option>{/each}</optgroup>
      </select></label>
    <label><span>Time step</span>
      <select value={store.step} onchange={(e) => store.set("step", e.currentTarget.value)}>
        <option value="">Any step</option>
        <option value="15min">15 minutes or finer</option>
        <option value="hourly">Hourly or finer</option>
        <option value="daily">Daily or finer</option>
        <option value="monthly">Monthly or finer</option>
      </select></label>
    <label><span>Re-hosting</span>
      <select value={store.reuse} onchange={(e) => store.set("reuse", e.currentTarget.value)}>
        <option value="">Any terms</option>
        <option value="open">Allowed, with or without credit</option>
        {#each Object.entries(TEXT.reuse) as [k, v] (k)}<option value={k}>{v}</option>{/each}
      </select></label>
    <label><span>Capacity</span>
      <select value={store.cap} onchange={(e) => store.set("cap", e.currentTarget.value)}>
        <option value="">Any</option>
        <option value="included">In the same data</option>
        <option value="any">In the same or a separate dataset</option>
      </select></label>
    <label><span>Status</span>
      <select value={store.status} onchange={(e) => store.set("status", e.currentTarget.value)}>
        <option value="">Any status</option>
        {#each Object.entries(TEXT.status) as [k, v] (k)}<option value={k}>{v}</option>{/each}
      </select></label>
    <label><span>Review</span>
      <select value={store.review} onchange={(e) => store.set("review", e.currentTarget.value)}>
        <option value="">Any review</option>
        <option value="reviewed">Reviewed by a person</option>
        <option value="unreviewed">Not yet reviewed</option>
      </select></label>
  </div>
  <p class="count" aria-live="polite">
    <span class="num"><b>{n}</b> {n === total ? `source${n === 1 ? "" : "s"}` : `of ${total} sources`}</span>
    {#if store.activeFilters}<button type="button" class="clear" onclick={() => store.clearFilters()}>Clear filters</button>{/if}
  </p>
</div>

<style>
  .filters { display: grid; gap: 10px; }
  .search { position: relative; display: block; }
  .search :global(.ic) { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: var(--ink-3); pointer-events: none; }
  input {
    width: 100%; height: 38px; padding: 0 12px 0 34px; border: 1px solid var(--line-strong); border-radius: var(--radius);
    background: var(--surface); font-size: 14px;
  }
  input::placeholder { color: var(--ink-3); }
  input:focus { outline: 2px solid var(--focus); outline-offset: -1px; border-color: transparent; }
  .sel { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
  .wide .sel { grid-template-columns: repeat(7, minmax(0, 1fr)); }
  label { display: grid; gap: 2px; min-width: 0; }
  label > span { font-size: 11.5px; font-weight: 500; color: var(--ink-3); }
  select {
    width: 100%; height: 32px; padding: 0 26px 0 8px; border: 1px solid var(--line); border-radius: var(--radius-sm);
    background: var(--surface) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath d='m4.5 6.5 3.5 3.5 3.5-3.5' fill='none' stroke='%2393a09a' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat right 6px center / 14px;
    appearance: none; font-size: 13px; text-overflow: ellipsis;
  }
  select:hover { border-color: var(--line-strong); }
  .count { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 13px; color: var(--ink-2); min-height: 26px; }
  .count b { color: var(--ink); font-weight: 600; }
  .clear { border: 0; background: none; padding: 2px 6px; color: var(--accent-ink); font-weight: 500; font-size: 13px; border-radius: var(--radius-sm); }
  .clear:hover { background: var(--accent-wash); }
  @media (max-width: 1100px) { .wide .sel { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
  @media (max-width: 420px) { .sel, .wide .sel { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  .ftoggle { display: none; }
  @media (max-width: 819px) {
    .ftoggle { display: inline-flex; align-items: center; gap: 4px; justify-self: start; height: 32px; padding: 0 10px 0 6px;
      border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--surface); font-size: 13px; font-weight: 500; color: var(--ink-2); }
    .ftoggle :global(.ic) { transition: transform 120ms ease; }
    .ftoggle[aria-expanded="true"] :global(.ic) { transform: rotate(90deg); }
    .sel:not(.open) { display: none; }
  }
</style>
