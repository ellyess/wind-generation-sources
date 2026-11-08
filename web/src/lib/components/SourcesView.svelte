<script lang="ts">
  import { hasLive } from "../live";
  import { LEVELS, store, type Indexed } from "../store.svelte";
  import { STEPS, TEXT, areaText, coverageText, plural } from "../text";
  import Filters from "./Filters.svelte";
  import Icon from "./Icon.svelte";
  import LevelDot from "./LevelDot.svelte";
  import SourceDetail from "./SourceDetail.svelte";
  import Verdict from "./Verdict.svelte";

  type Key = "name" | "area" | "level" | "step" | "cov" | "reuse" | "traps";
  let sort = $state<{ key: Key; dir: 1 | -1 }>({ key: "area", dir: 1 });
  const REUSE = Object.keys(TEXT.reuse);
  const val: Record<Key, (s: Indexed) => string | number> = {
    name: (s) => s.name.toLowerCase(),
    area: (s) => (s.countries.length > 3 ? "~" : store.placeName(s.countries[0])),
    level: (s) => LEVELS.indexOf(s.level),
    step: (s) => STEPS.indexOf(s.resolution),
    cov: (s) => s.coverage.start,
    reuse: (s) => REUSE.indexOf(s.licence.redistribution),
    traps: (s) => -(s.traps ?? []).length,
  };
  let rows = $derived(store.shown.slice().sort((a, b) => {
    const x = val[sort.key](a), y = val[sort.key](b);
    return (x < y ? -1 : x > y ? 1 : a.id.localeCompare(b.id)) * sort.dir;
  }));
  const by = (key: Key) => (sort = { key, dir: sort.key === key ? (-sort.dir as 1 | -1) : 1 });
  const aria = (key: Key) => (sort.key === key ? (sort.dir === 1 ? "ascending" : "descending") : "none");
  let src = $derived(store.source ? store.byId.get(store.source) : undefined);
  const now = new Date().getFullYear();
  const Y0 = 1990;
  const pos = (y: number) => `${Math.max(0, ((y - Y0) / (now + 1 - Y0)) * 100).toFixed(2)}%`;

  // Opening a source moves focus into the drawer and keeps its row in view; closing returns focus to the row.
  let drawer = $state<HTMLElement>();
  let lastOpen = "";
  $effect(() => {
    const id = src?.id;
    if (id && drawer) {
      lastOpen = id;
      drawer.focus({ preventScroll: true });
      document.querySelector(`.sources tr[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: "nearest" });
    } else if (!id && lastOpen) {
      (document.querySelector(`.sources tr[data-id="${CSS.escape(lastOpen)}"] .open`) as HTMLElement | null)?.focus();
      lastOpen = "";
    }
  });

  // On phones the drawer covers the list, so the list leaves the tab order while it is open.
  const narrowQ = matchMedia("(max-width: 819px)");
  let narrow = $state(narrowQ.matches);
  $effect(() => {
    const on = () => (narrow = narrowQ.matches);
    narrowQ.addEventListener("change", on);
    return () => narrowQ.removeEventListener("change", on);
  });

  // Escape closes the drawer, except while typing, where it clears the search box instead.
  function onKey(e: KeyboardEvent) {
    const typing = (e.target as Element | null)?.closest("input, select, textarea");
    if (e.key === "Escape" && src && !typing) store.go({ source: "" });
  }
  const cols: [Key, string][] = [["name", "Source"], ["area", "Area"], ["level", "Level"], ["step", "Step"], ["cov", "Coverage"], ["reuse", "Re-hosting"], ["traps", "Traps"]];
</script>

<svelte:window onkeydown={onKey} />

<div class="sources" class:has-detail={!!store.source}>
  <div class="main" inert={narrow && !!store.source}>
    <header>
      <h1>All sources</h1>
      {#if store.country}<p class="pick">Showing {store.placeName(store.country)} only. <button type="button" onclick={() => store.go({ country: "" })}>Show every country</button></p>{/if}
    </header>
    <Filters wide />
    <div class="table-wrap">
      <table>
        <caption class="visually-hidden">Wind generation sources; choose a row for its access, licence, traps and checks. Column headers sort.</caption>
        <thead>
          <tr>
            {#each cols as [k, label] (k)}
              <th scope="col" aria-sort={aria(k)} class={k}>
                <button type="button" onclick={() => by(k)}>{label}<span class="arr" aria-hidden="true">{sort.key === k ? (sort.dir === 1 ? "↑" : "↓") : ""}</span></button>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each rows as s (s.id)}
            <tr data-id={s.id} class:on={store.source === s.id} onclick={(e) => { if (!(e.target as Element).closest("a")) store.go({ source: s.id }); }}>
              <th scope="row" class="name">
                <a class="open" {...store.link({ source: s.id })}>{s.name}</a>
                <span class="pub">{s.publisher}
                  {#if hasLive(s.id)}<span class="tag live"><Icon name="live" size={11} />Live</span>{/if}
                  {#if s.reviewed !== false}<span class="tag rev"><Icon name="check" size={11} />Reviewed</span>{/if}
                  {#if s.status !== "active"}<span class="tag">{TEXT.status[s.status]}</span>{/if}
                </span>
                <span class="m-meta"><span>{areaText(s.countries, store.placeName)}</span><span class="mm-lv">{" · "}<span class="lv"><LevelDot tier={s._tier} />{TEXT.level[s.level]}</span></span><span>{" · "}{TEXT.step[s.resolution]}</span><span class="mm-cov">{" · "}<span class="num">{coverageText(s.coverage)}</span></span></span>
                <span class="m-verdict"><Verdict value={s.licence.redistribution} /></span>
              </th>
              <td class="area">{areaText(s.countries, store.placeName)}</td>
              <td class="level"><span class="lv"><LevelDot tier={s._tier} />{TEXT.level[s.level]}</span></td>
              <td class="step">{TEXT.step[s.resolution]}</td>
              <td class="cov">
                <span class="mini" aria-hidden="true"><i style:left={pos(s.coverage.start)} style:right="calc(100% - {pos((s.coverage.end ?? now) + 1)})" style:--c="var(--l{s._tier})"></i></span>
                <span class="num">{coverageText(s.coverage)}</span>
              </td>
              <td class="reuse"><Verdict value={s.licence.redistribution} /></td>
              <td class="traps num" class:zero={!(s.traps ?? []).length}>{(s.traps ?? []).length}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      {#if !rows.length}<p class="empty">No source matches these filters. <button type="button" onclick={() => store.clearFilters()}>Clear filters</button></p>{/if}
    </div>
  </div>

  {#if src}
    <aside class="drawer" aria-label="Source detail" tabindex="-1" bind:this={drawer}>
      <button type="button" class="close" onclick={() => store.go({ source: "" })} aria-label="Close the detail"><Icon name="close" /></button>
      <SourceDetail s={src} heading="h2" />
    </aside>
  {:else if store.source}
    <aside class="drawer" aria-label="Source detail" tabindex="-1">
      <button type="button" class="close" onclick={() => store.go({ source: "" })} aria-label="Close"><Icon name="close" /></button>
      <h2 class="missing">No source called <code>{store.source}</code></h2>
      <p class="missing-p">It may have been renamed or removed. Search the table for its publisher instead.</p>
    </aside>
  {/if}
</div>

<style>
  .sources { display: grid; grid-template-columns: minmax(0, 1fr); height: 100%; min-height: 0; }
  .sources.has-detail { grid-template-columns: minmax(0, 1fr) min(520px, 42vw); }
  .main { container-type: inline-size; overflow-y: auto; padding: 24px 28px 48px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-content: start; }
  .main > :global(*) { width: 100%; max-width: 1480px; justify-self: center; }
  header { display: grid; gap: 4px; }
  h1 { font-size: 22px; letter-spacing: -0.02em; }
  .pick { font-size: 13px; color: var(--ink-2); }
  .pick button, .empty button { border: 0; background: none; padding: 0; color: var(--accent-ink); text-decoration: underline; }
  .table-wrap { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
  thead th { position: sticky; top: 0; z-index: 1; background: var(--surface); border-bottom: 1px solid var(--line-strong); text-align: left; padding: 0; }
  thead button { display: flex; gap: 4px; width: 100%; padding: 10px 12px; border: 0; background: none; font-size: 12px; font-weight: 600; color: var(--ink-2); text-align: left; white-space: nowrap; }
  thead button:hover { color: var(--ink); }
  .arr { color: var(--accent); }
  tbody tr { border-bottom: 1px solid var(--line); cursor: pointer; }
  tbody tr:hover { background: var(--surface-2); }
  tbody tr.on { background: var(--accent-wash); }
  td, tbody th { padding: 9px 12px; vertical-align: top; text-align: left; font-weight: 400; }
  .name { min-width: 18rem; max-width: 34rem; }
  .open { display: block; padding: 3px 0; margin: -3px 0; text-align: left; font-weight: 600; line-height: 1.35; overflow-wrap: anywhere; color: var(--ink); text-decoration: none; }
  .open:hover { color: var(--accent-ink); }
  .pub { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; margin-top: 2px; font-size: 12.5px; color: var(--ink-2); }
  .area { color: var(--ink-2); min-width: 8rem; }
  .lv { display: inline-flex; align-items: center; gap: 7px; white-space: nowrap; }
  .step { white-space: nowrap; }
  .cov { white-space: nowrap; min-width: 9rem; }
  .mini { position: relative; display: block; height: 4px; margin: 6px 0 4px; background: var(--surface-3); border-radius: 2px; }
  .mini i { position: absolute; top: 0; bottom: 0; background: var(--c); border-radius: 2px; }
  .cov .num { font-size: 12.5px; color: var(--ink-2); }
  .traps { text-align: right; font-weight: 600; color: var(--ink); }
  .traps.zero { color: var(--ink-3); font-weight: 400; }
  th.traps button { justify-content: flex-end; }
  .m-verdict, .m-meta { display: none; }
  .m-meta { margin-top: 3px; font-size: 12.5px; color: var(--ink-2); }
  .m-meta .lv { gap: 5px; }
  .tag { display: inline-flex; align-items: center; gap: 3px; padding: 0 6px; height: 18px; border-radius: 9px; background: var(--surface-3); font-size: 11px; font-weight: 500; }
  .tag.live { background: var(--accent-wash); color: var(--accent-ink); }
  .tag.rev { gap: 3px; background: none; border: 1px solid var(--line-strong); color: var(--ink-2); }
  .empty { padding: 20px; font-size: 13.5px; color: var(--ink-2); }
  .drawer { --detail-bg: var(--surface); --toc-top: -24px; position: relative; overflow-y: auto; padding: 24px 24px 48px; background: var(--surface); border-left: 1px solid var(--line); box-shadow: var(--shadow-2); }
  .drawer :global(.detail > header) { padding-right: 40px; }
  .drawer:focus { outline: none; }
  .missing { font-size: 18px; padding-right: 40px; overflow-wrap: anywhere; }
  .missing code { font-family: var(--mono); font-size: 0.85em; }
  .missing-p { margin-top: 8px; color: var(--ink-2); font-size: 14px; }
  .close { position: absolute; top: 14px; right: 14px; width: 32px; height: 32px; display: grid; place-items: center; border: 0; border-radius: var(--radius-sm); background: var(--surface-3); }
  /* Columns drop by the table's own width, so an open drawer narrows the table too. */
  /* Hidden columns move into a line under the name: Area and Step first, the rest below 760px. */
  .mm-lv, .mm-cov { display: none; }
  @container (max-width: 1050px) {
    .area, th.area, .step, th.step { display: none; }
    .m-meta { display: block; }
  }
  @container (max-width: 760px) {
    .cov, th.cov, .level, th.level, .reuse, th.reuse { display: none; }
    .mm-lv, .mm-cov { display: inline; }
    .m-verdict { display: block; }
    .m-verdict { margin-top: 4px; font-size: 12.5px; }
    .name { min-width: 0; }
  }
  @media (max-width: 819px) {
    .main { padding: 16px; }
    .sources.has-detail { grid-template-columns: 1fr; }
    .drawer { --toc-top: -20px; position: fixed; inset: var(--top) 0 0 0; z-index: 20; padding: 20px 16px 48px; }
  }
</style>
