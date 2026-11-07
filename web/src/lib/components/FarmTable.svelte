<script lang="ts" module>
  /** How a farm point was placed, in plain words: a short cell label and a line for the key. */
  export const PLACED: Record<string, { short: string; via?: string; how: string }> = {
    osm: { short: "Name match", via: "OpenStreetMap", how: "matched to the unit by name, not reviewed" },
    repd: { short: "Name match", via: "Renewable Energy Planning Database", how: "matched to the unit by name, not reviewed" },
    wikidata: { short: "ID link", via: "Wikidata", how: "linked to the unit by its balancing mechanism ID on Wikidata, not reviewed" },
    "os-codepoint-open": { short: "Postcode", via: "OS Code-Point Open", how: "approximate, at the station's postcode centre, not at the turbine" },
    publisher: { short: "Publisher", how: "where the publisher says it is" },
    ens: { short: "Register", via: "Danish Energy Agency", how: "the publisher's own turbine register" },
    "eia-860": { short: "Register", via: "EIA-860", how: "the publisher's own plant register" },
  };
  const ROUND = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const TENTH = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });
  const HUNDREDTH = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });
  /** A capacity in MW, with fewer decimals as it grows. */
  export const mwText = (mw: number) => (mw >= 100 ? ROUND : mw >= 10 ? TENTH : HUNDREDTH).format(mw);
</script>

<script lang="ts">
  import { store } from "../store.svelte";

  /** `rows` are indices into store.farms.farms, which are also the map's feature ids. */
  let { rows, showSource = false }: { rows: number[]; showSource?: boolean } = $props();

  const PAGE = 200;
  type Key = "name" | "mw";
  let sort = $state<{ key: Key; dir: 1 | -1 }>({ key: "mw", dir: -1 });
  let limit = $state(PAGE);
  $effect(() => { void rows; limit = PAGE; });

  const farms = $derived(store.farms?.farms ?? []);
  const collate = new Intl.Collator("en", { sensitivity: "base", numeric: true }).compare;
  let sorted = $derived.by(() => {
    const { key, dir } = sort;
    return rows.slice().sort((a, b) => {
      const x = farms[a], y = farms[b];
      if (key === "mw") {
        // Unknown capacities go last whichever way the column sorts.
        if (x.mw == null || y.mw == null) return (x.mw == null ? 1 : 0) - (y.mw == null ? 1 : 0) || collate(x.name, y.name);
        return (x.mw - y.mw) * dir || collate(x.name, y.name);
      }
      return collate(x.name, y.name) * dir;
    });
  });
  let total = $derived(rows.reduce((t, i) => t + (farms[i].mw ?? 0), 0));
  let sized = $derived(rows.filter((i) => farms[i].mw != null).length);
  // Name each row's source by its publisher, or by the entry's name where two here share one.
  let label = $derived.by(() => {
    const entries = [...new Set(rows.map((i) => farms[i].entry))];
    const pub = (e: string) => store.byId.get(e)?.publisher ?? e;
    const seen = new Map<string, number>();
    for (const e of entries) seen.set(pub(e), (seen.get(pub(e)) ?? 0) + 1);
    return new Map(entries.map((e) => [e, seen.get(pub(e)) === 1 ? pub(e) : (store.byId.get(e)?.name ?? e)]));
  });
  let key = $derived([...new Set(rows.map((i) => farms[i].located_by))].filter((k) => PLACED[k]));

  const by = (k: Key) => (sort = { key: k, dir: sort.key === k ? (-sort.dir as 1 | -1) : k === "mw" ? -1 : 1 });
  const aria = (k: Key) => (sort.key === k ? (sort.dir === 1 ? "ascending" : "descending") : "none");
  const arrow = (k: Key) => (sort.key === k ? (sort.dir === 1 ? "↑" : "↓") : "");
  const gw = (mw: number) => (mw >= 1000 ? `${TENTH.format(mw / 1000)} GW` : `${ROUND.format(mw)} MW`);
</script>

{#if rows.length}
  <section class="farms" aria-label="Located farms and turbines">
    <h3>On the map <span class="sub num">{rows.length.toLocaleString("en-GB")} {rows.length === 1 ? "point" : "points"}{sized ? `, ${gw(total)}` : ""}</span></h3>
    <p class="hint">Farms or turbines whose own output is published{sized && sized < rows.length ? `; capacity known for ${sized.toLocaleString("en-GB")}` : ""}. Choose one to find it on the map.</p>
    <div class="wrap">
      <table>
        <caption class="visually-hidden">Located farms and turbines; choose a row to show it on the map. Column headers sort.</caption>
        <thead>
          <tr>
            <th scope="col" aria-sort={aria("name")}><button type="button" onclick={() => by("name")}>Name<span class="arr" aria-hidden="true">{arrow("name")}</span></button></th>
            <th scope="col" class="mw" aria-sort={aria("mw")}><button type="button" onclick={() => by("mw")}>MW<span class="arr" aria-hidden="true">{arrow("mw")}</span></button></th>
            <th scope="col" class="how"><span>Placed by</span></th>
          </tr>
        </thead>
        <tbody>
          {#each sorted.slice(0, limit) as id (id)}
            {@const f = farms[id]}
            {@const p = PLACED[f.located_by]}
            <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
            <tr class:on={store.focusFarm === id} class:hot={store.hoverFarm === id} onclick={() => (store.focusFarm = id)}>
              <th scope="row">
                <button type="button" class="nm" onclick={(e) => { e.stopPropagation(); store.focusFarm = id; }}>{f.name}</button>
                {#if showSource}<span class="src" title={store.byId.get(f.entry)?.name}>{label.get(f.entry)}</span>{/if}
              </th>
              <td class="mw num">{#if f.mw != null}{mwText(f.mw)}{:else}<span class="unk" title="Capacity not published">–</span>{/if}</td>
              <td class="how" title={p ? `${p.via ? `${p.via}: ` : ""}${p.how}` : f.located_by}>{p?.short ?? f.located_by}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if sorted.length > limit}
      <button type="button" class="more" onclick={() => (limit += PAGE)}>Show {Math.min(PAGE, sorted.length - limit)} more <span class="sub num">{limit.toLocaleString("en-GB")} of {sorted.length.toLocaleString("en-GB")} shown</span></button>
    {/if}
    {#if key.length}
      <dl class="key">
        {#each key as k (k)}<div><dt>{PLACED[k].short}{PLACED[k].via ? ` (${PLACED[k].via})` : ""}</dt><dd>{PLACED[k].how}</dd></div>{/each}
      </dl>
    {/if}
  </section>
{/if}

<style>
  .farms { display: grid; gap: 8px; }
  h3 { font-size: 15px; margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline; }
  .sub { font-size: 12.5px; font-weight: 400; color: var(--ink-3); }
  .hint { font-size: 12.5px; color: var(--ink-3); margin-top: -4px; }
  .wrap { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: clip; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }
  thead th { background: var(--surface); border-bottom: 1px solid var(--line-strong); text-align: left; padding: 0; font-size: 12px; font-weight: 600; color: var(--ink-2); }
  thead button, thead span { display: flex; align-items: baseline; gap: 4px; width: 100%; padding: 8px 10px; border: 0; background: none; font: inherit; color: inherit; text-align: left; white-space: nowrap; }
  thead button:hover { color: var(--ink); }
  th.mw button { justify-content: flex-end; }
  .arr { color: var(--accent); }
  .mw { width: 4.6rem; text-align: right; }
  .how { width: 6.4rem; }
  tbody tr { border-bottom: 1px solid var(--line); cursor: pointer; }
  tbody tr:last-child { border-bottom: 0; }
  tbody tr:hover, tbody tr.hot { background: var(--surface-2); }
  tbody tr.on { background: var(--accent-wash); }
  tbody th, td { padding: 6px 10px; vertical-align: top; text-align: left; font-weight: 400; }
  td.mw { text-align: right; color: var(--ink); }
  td.how { color: var(--ink-2); font-size: 12.5px; }
  .nm { display: block; max-width: 100%; border: 0; background: none; padding: 0; text-align: left; font-weight: 500; color: var(--ink); line-height: 1.35; overflow-wrap: anywhere; }
  .nm:hover { color: var(--accent-ink); }
  .src { display: block; margin-top: 1px; font-size: 12px; color: var(--ink-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .unk { color: var(--ink-3); }
  .more { justify-self: start; display: inline-flex; gap: 8px; align-items: baseline; border: 0; background: none; padding: 4px 6px; margin-left: -6px;
    border-radius: var(--radius-sm); color: var(--accent-ink); font-size: 13px; font-weight: 500; }
  .more:hover { background: var(--accent-wash); }
  .key { margin: 0; display: grid; gap: 2px; font-size: 12px; color: var(--ink-3); }
  .key div { display: flex; flex-wrap: wrap; gap: 0 6px; }
  .key dt { color: var(--ink-2); font-weight: 500; }
  .key dt::after { content: ":"; }
  .key dd { margin: 0; }
  @media (max-width: 360px) {
    .how { width: 5.4rem; }
    tbody th, td { padding: 6px 8px; }
    thead button, thead span { padding: 8px; }
  }
</style>
