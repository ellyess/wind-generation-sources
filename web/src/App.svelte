<script lang="ts">
  import { onMount } from "svelte";
  import { load, store } from "./lib/store.svelte";
  import About from "./lib/components/About.svelte";
  import ChecksView from "./lib/components/ChecksView.svelte";
  import Panel from "./lib/components/Panel.svelte";
  import SourcesView from "./lib/components/SourcesView.svelte";
  import TopBar from "./lib/components/TopBar.svelte";

  // The map library is the heaviest part, so it loads after the panel can be used.
  const mapView = import("./lib/components/MapView.svelte");

  onMount(() => {
    store.readURL();
    load();
    const pop = () => store.readURL();
    addEventListener("popstate", pop);
    return () => removeEventListener("popstate", pop);
  });

  // Filters and search update the address in place, so a filtered view can be shared.
  $effect(() => {
    void [store.level, store.step, store.reuse, store.status, store.review, store.region, store.q];
    if (store.cat) history.replaceState(null, "", store.url());
  });

  $effect(() => {
    const s = store.source ? store.byId.get(store.source) : undefined;
    const c = store.country ? store.placeName(store.country) : "";
    document.title = [s?.name, c, "Wind Generation Sources"].filter(Boolean).join(" · ");
  });
</script>

<TopBar />
<main class="stage" data-view={store.view}>
  {#if store.error}
    <p class="fatal">The catalogue could not be loaded ({store.error}). Reload the page, or download <a href="./data/catalogue.csv">catalogue.csv</a> directly.</p>
  {:else if !store.cat}
    <p class="loading">Loading the catalogue.</p>
  {:else if store.view === "map"}
    <div class="mapview"><Panel />
      {#await mapView}<div class="map-wrap"></div>{:then m}<m.default />{:catch}<p class="loading">The map could not load; the lists still work.</p>{/await}
    </div>
  {:else if store.view === "sources"}
    <SourcesView />
  {:else if store.view === "checks"}
    <ChecksView />
  {:else}
    <About />
  {/if}
</main>

<style>
  .stage { height: calc(100dvh - var(--top)); min-height: 0; }
  .mapview { display: grid; grid-template-columns: var(--panel-w) minmax(0, 1fr); height: 100%; min-height: 0; }
  .fatal, .loading { padding: 24px; color: var(--ink-2); }
  @media (max-width: 1100px) { .mapview { grid-template-columns: 380px minmax(0, 1fr); } }
  @media (max-width: 819px) {
    .stage[data-view="map"] { height: auto; }
    .mapview { display: flex; flex-direction: column-reverse; height: auto; }
    .mapview :global(.map-wrap) { height: 40vh; min-height: 280px; }
    .mapview :global(.panel) { overflow: visible; }
  }
</style>
