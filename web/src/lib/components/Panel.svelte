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
  const back = () => (history.length > 1 ? history.back() : store.go({ source: "" }));
</script>

<aside class="panel" bind:this={el} aria-label="Catalogue panel">
  {#if src}
    <button type="button" class="back" onclick={back}><Icon name="back" />{store.country ? store.placeName(store.country) : "Back"}</button>
    <SourceDetail s={src} />
  {:else if store.country}
    <CountryView code={store.country} />
  {:else}
    <Overview />
  {/if}
</aside>

<style>
  .panel { overflow-y: auto; overscroll-behavior: contain; padding: 20px 20px 40px; background: var(--surface-2); border-right: 1px solid var(--line); }
  .back { display: inline-flex; align-items: center; gap: 4px; margin: -6px 0 12px -6px; padding: 4px 8px 4px 4px; border: 0;
    background: none; border-radius: var(--radius-sm); color: var(--accent-ink); font-weight: 500; font-size: 13px; }
  .back:hover { background: var(--accent-wash); }
  @media (max-width: 819px) { .panel { padding: 16px 16px 40px; border-right: 0; border-top: 1px solid var(--line); } }
</style>
