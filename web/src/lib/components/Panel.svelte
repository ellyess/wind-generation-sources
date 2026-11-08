<script lang="ts">
  import { store } from "../store.svelte";
  import CountryView from "./CountryView.svelte";
  import Icon from "./Icon.svelte";
  import Overview from "./Overview.svelte";
  import SourceDetail from "./SourceDetail.svelte";

  let el: HTMLElement;
  let src = $derived(store.source ? store.byId.get(store.source) : undefined);
  // Start each new view at the top of the panel, with focus on its heading so keyboard and
  // screen-reader users land on the new content (not on the first load).
  let first = true;
  $effect(() => {
    void store.source; void store.country;
    el?.scrollTo({ top: 0 });
    if (first) { first = false; return; }
    queueMicrotask(() => {
      const h = el?.querySelector("h1");
      if (!h) return;
      h.setAttribute("tabindex", "-1");
      h.focus({ preventScroll: true });
    });
  });
  // Back always stays on the site: to the country the source was opened from, or to the list.
  // A link straight to a one-country source goes back to that country.
  let backTo = $derived(!store.country && src?.countries.length === 1 ? { source: "", country: src.countries[0] } : { source: "" });
  let backLabel = $derived(store.country ? store.placeName(store.country)
    : src?.countries.length === 1 ? store.placeName(src.countries[0])
    : store.q || store.activeFilters ? "Back to results" : "All countries");
</script>

<aside class="panel" bind:this={el} aria-label="Catalogue panel">
  {#if src}
    <a class="back" {...store.link(backTo)}><Icon name="back" />{backLabel}</a>
    <SourceDetail s={src} />
  {:else if store.source}
    <a class="back" {...store.link(backTo)}><Icon name="back" />{backLabel}</a>
    <h1 class="missing">No source called <code>{store.source}</code></h1>
    <p class="missing-p">It may have been renamed or removed. Search the catalogue for its publisher instead.</p>
  {:else if store.country && store.sources.length && !store.catalogued.has(store.country)}
    <a class="back" {...store.link({ country: "" })}><Icon name="back" />All countries</a>
    <h1 class="missing">Nothing catalogued for {store.placeName(store.country)}</h1>
    <p class="missing-p">No source in the catalogue covers <code>{store.country}</code> yet. Search the catalogue, or see the research backlog for leads.</p>
  {:else if store.country}
    <CountryView code={store.country} />
  {:else}
    <Overview />
  {/if}
</aside>

<style>
  /* --toc-top: the source page's sticky index sits flush with the panel's top edge, over its padding. */
  .panel { --toc-top: -20px; overflow-y: auto; overscroll-behavior: contain; padding: 20px 20px 40px; background: var(--surface-2); border-right: 1px solid var(--line); }
  .back { justify-self: start; width: fit-content; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; margin: -6px 0 12px -6px; padding: 4px 8px 4px 4px; border: 0;
    background: none; border-radius: var(--radius-sm); color: var(--accent-ink); font-weight: 500; font-size: 13px; }
  .back:hover { background: var(--accent-wash); }
  .panel :global(h1:focus) { outline: none; }
  .missing { font-size: 20px; color: var(--ink); overflow-wrap: anywhere; }
  .missing code { font-family: var(--mono); font-size: 0.85em; }
  .missing-p { margin-top: 8px; color: var(--ink-2); font-size: 14px; }
  @media (max-width: 819px) { .panel { --toc-top: 0; padding: 16px 16px 40px; border-right: 0; border-top: 1px solid var(--line); } }
</style>
