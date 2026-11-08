<script lang="ts">
  import { store } from "../store.svelte";
  import CountryView from "./CountryView.svelte";
  import Icon from "./Icon.svelte";
  import Overview from "./Overview.svelte";
  import SourceDetail from "./SourceDetail.svelte";

  let el: HTMLElement;
  let src = $derived(store.source ? store.byId.get(store.source) : undefined);
  // Start each new view at the top of the panel.
  $effect(() => { void store.source; void store.country; el?.scrollTo({ top: 0 }); });
  // Back always stays on the site: to the country the source was opened from, or to the list.
  const back = () => store.go({ source: "" });
  let backLabel = $derived(store.country ? store.placeName(store.country)
    : store.q || store.activeFilters ? "Back to results" : "All countries");
</script>

<aside class="panel" bind:this={el} aria-label="Catalogue panel">
  {#if src}
    <button type="button" class="back" onclick={back}><Icon name="back" />{backLabel}</button>
    <SourceDetail s={src} />
  {:else if store.country}
    <CountryView code={store.country} />
  {:else}
    <Overview />
  {/if}
</aside>

<style>
  /* --toc-top: the source page's sticky index sits flush with the panel's top edge, over its padding. */
  .panel { --toc-top: -20px; overflow-y: auto; overscroll-behavior: contain; padding: 20px 20px 40px; background: var(--surface-2); border-right: 1px solid var(--line); }
  .back { display: inline-flex; align-items: center; gap: 4px; margin: -6px 0 12px -6px; padding: 4px 8px 4px 4px; border: 0;
    background: none; border-radius: var(--radius-sm); color: var(--accent-ink); font-weight: 500; font-size: 13px; }
  .back:hover { background: var(--accent-wash); }
  @media (max-width: 819px) { .panel { --toc-top: 0; padding: 16px 16px 40px; border-right: 0; border-top: 1px solid var(--line); } }
</style>
