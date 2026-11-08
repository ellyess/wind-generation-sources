<script lang="ts">
  import { REPO, store, type View } from "../store.svelte";
  import Icon from "./Icon.svelte";

  const TABS: [View, string][] = [["map", "Map"], ["sources", "Sources"], ["checks", "Checks"], ["about", "About"]];
</script>

<header class="bar">
  <button type="button" class="brand" onclick={() => store.go({ view: "map", country: "", source: "" })}>
    <img src="./favicon.svg" alt="" width="24" height="24" /><span>Wind Generation Sources</span>
  </button>
  <nav aria-label="Views">
    {#each TABS as [v, label] (v)}
      <button type="button" class:on={store.view === v} aria-current={store.view === v ? "page" : undefined}
        onclick={() => store.go({ view: v, source: v === "map" || v === "sources" ? store.source : "" })}>{label}</button>
    {/each}
  </nav>
  <div class="act">
    <a href="./data/catalogue.csv" download class="btn" aria-label="Download the catalogue as CSV"><Icon name="download" /><span>CSV</span></a>
    <a href="./data/catalogue.json" class="btn" aria-label="The catalogue as JSON"><Icon name="code" /><span>JSON</span></a>
    <a href={REPO} class="btn" target="_blank" rel="noopener"><span>GitHub</span></a>
  </div>
</header>

<style>
  .bar { height: var(--top); display: flex; align-items: center; gap: 20px; padding: 0 16px; background: var(--surface); border-bottom: 1px solid var(--line); position: relative; z-index: 10; }
  .brand { display: inline-flex; align-items: center; gap: 10px; border: 0; background: none; padding: 0; font-weight: 650; font-size: 15px; letter-spacing: -0.01em; white-space: nowrap; }
  .brand img { border-radius: 6px; }
  nav { display: flex; gap: 2px; height: 100%; }
  nav button { position: relative; height: 100%; padding: 0 12px; border: 0; background: none; font-size: 14px; font-weight: 500; color: var(--ink-2); }
  nav button:hover { color: var(--ink); }
  nav button.on { color: var(--ink); }
  nav button.on::after { content: ""; position: absolute; left: 10px; right: 10px; bottom: -1px; height: 2px; background: var(--accent); border-radius: 2px 2px 0 0; }
  .act { margin-left: auto; display: flex; gap: 4px; align-items: center; }
  .btn { display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 10px; border: 0; border-radius: var(--radius-sm); background: none; color: var(--ink-2); font-size: 13px; font-weight: 500; text-decoration: none; }
  .btn:hover { background: var(--surface-3); color: var(--ink); }
  @media (max-width: 900px) { .act .btn span { display: none; } .act a.btn:nth-child(3) { display: none; } }
  @media (max-width: 640px) {
    .bar { gap: 8px; padding: 0 8px 0 12px; }
    .brand span { display: none; }
    nav button { padding: 0 9px; font-size: 13.5px; }
    .act a.btn { display: none; }
  }
  @media (max-width: 360px) {
    .bar { gap: 4px; padding: 0 4px 0 10px; }
    nav button { padding: 0 7px; font-size: 13px; }
    nav button.on::after { left: 6px; right: 6px; }
  }
</style>
