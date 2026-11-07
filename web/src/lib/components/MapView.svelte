<script lang="ts">
  import * as maplibregl from "maplibre-gl";
  import type { ErrorEvent, ExpressionSpecification, GeoJSONSource, Map as MLMap, MapGeoJSONFeature, MapMouseEvent } from "maplibre-gl";
  import type * as GeoJSON from "geojson";
  import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

  maplibregl.setWorkerUrl(workerUrl);
  import { onMount } from "svelte";
  import { store } from "../store.svelte";
  import { TIER_TEXT, plural } from "../text";
  import Icon from "./Icon.svelte";
  import LevelDot from "./LevelDot.svelte";

  const STYLE = { light: "https://tiles.openfreemap.org/styles/positron", dark: "https://tiles.openfreemap.org/styles/dark" };
  const WORLD: [number, number, number, number] = [-168, -50, 178, 72];
  // Locations matched to units by name (crosswalk/build.py); the rest come from the publisher.
  const MATCHED = new Set(["osm", "repd"]);
  const located = $derived([...new Set((store.farms?.farms ?? [])
    .map((f) => store.placeName(store.byId.get(f.entry)?.countries[0] ?? "")))].join(", "));

  let host: HTMLDivElement;
  let map: MLMap | null = null;
  let ready = $state(false);
  let failed = $state("");
  let globe = $state(false);
  let keyOpen = $state(false);
  let outlines: GeoJSON.FeatureCollection | null = null;
  let bounds = new Map<string, [number, number, number, number]>();
  let hovered: string | null = null;
  let tip = $state<{ x: number; y: number; title: string; lines: string[] } | null>(null);

  const dark = () => {
    const t = document.documentElement.dataset.theme;
    return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  };
  const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  /** Bounding box of a country's largest polygon, so overseas territories do not zoom to the globe. */
  function mainBox(g: GeoJSON.Geometry): [number, number, number, number] {
    const polys = g.type === "MultiPolygon" ? g.coordinates : g.type === "Polygon" ? [g.coordinates] : [];
    let best: number[][] = [];
    let bestArea = -1;
    for (const p of polys) {
      const ring = p[0];
      let a = 0;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) a += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1]);
      if (Math.abs(a) > bestArea) { bestArea = Math.abs(a); best = ring; }
    }
    const xs = best.map((c) => c[0]), ys = best.map((c) => c[1]);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  }

  function addLayers() {
    if (!map || !outlines) return;
    const m = map;
    m.addSource("countries", { type: "geojson", data: outlines, promoteId: "iso" });
    const before = m.getLayer("water") ? "water" : undefined;
    // Roads and rail read as noise over a country fill; show them only when zoomed right in.
    for (const l of m.getStyle().layers) {
      const sl = (l as { "source-layer"?: string })["source-layer"];
      if (sl === "transportation" || sl === "transportation_name") m.setLayerZoomRange(l.id, 8, 24);
    }
    const tierColour: ExpressionSpecification = ["match", ["coalesce", ["feature-state", "tier"], 0],
      1, css("--l1"), 2, css("--l2"), 3, css("--l3"), 4, css("--l4"), css("--l0")];
    m.addLayer({ id: "country-fill", type: "fill", source: "countries",
      paint: {
        "fill-color": tierColour,
        "fill-opacity": ["interpolate", ["linear"], ["zoom"],
          1, ["case", ["boolean", ["feature-state", "cat"], false], 0.92, 0],
          5, ["case", ["boolean", ["feature-state", "cat"], false], 0.6, 0],
          8, ["case", ["boolean", ["feature-state", "cat"], false], 0.45, 0]],
      } }, before);
    m.addLayer({ id: "country-hover", type: "line", source: "countries",
      paint: { "line-color": css("--ink"), "line-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.55, 0],
        "line-width": 1 } });
    m.addLayer({ id: "country-picked", type: "line", source: "countries",
      paint: { "line-color": css("--ink"), "line-opacity": ["case", ["boolean", ["feature-state", "picked"], false], 1, 0],
        "line-width": 2 } });
    m.addSource("farms", { type: "geojson", data: farmData() });
    m.addLayer({ id: "farms", type: "circle", source: "farms",
      paint: {
        "circle-color": css("--farm"),
        // Single turbines (Denmark's register) draw smaller so a dense fleet does not hide the country.
        "circle-radius": ["interpolate", ["linear"], ["zoom"],
          2, ["case", ["get", "turbine"], 0.8, 2.2], 6, ["case", ["get", "turbine"], 1.8, 4.5],
          10, ["case", ["get", "turbine"], 4.5, 7]],
        "circle-stroke-color": dark() ? "#0e1114" : "#ffffff",
        "circle-stroke-width": ["interpolate", ["linear"], ["zoom"],
          2, ["case", ["get", "turbine"], 0, 0.6], 8, ["case", ["get", "turbine"], 0.8, 1.5]],
        "circle-opacity": ["case", ["boolean", ["get", "shown"], true], 1, 0.15],
        "circle-stroke-opacity": ["case", ["boolean", ["get", "shown"], true], 1, 0.15],
      } });
    paint();
    ready = true;
  }

  function farmData(): GeoJSON.FeatureCollection {
    const shown = new Set(store.filtered.map((s) => s.id));
    return { type: "FeatureCollection", features: (store.farms?.farms ?? []).map((f, i) => ({
      type: "Feature", id: i, geometry: { type: "Point", coordinates: [f.lon, f.lat] },
      properties: { name: f.name, entry: f.entry, units: f.n, shown: shown.has(f.entry),
        turbine: !!f.turbine, matched: MATCHED.has(f.located_by) },
    })) };
  }

  function paint() {
    if (!map || !outlines || !map.getSource("countries")) return;
    for (const f of outlines.features) {
      const iso = f.properties?.iso;
      if (!iso) continue;
      map.setFeatureState({ source: "countries", id: iso }, {
        tier: store.tiers.get(iso) ?? 0,
        cat: store.catalogued.has(iso),
        picked: store.country === iso,
      });
    }
    (map.getSource("farms") as GeoJSONSource | undefined)?.setData(farmData());
  }

  // Repaint when filters or the pick change.
  $effect(() => {
    void store.tiers; void store.country; void store.filtered;
    paint();
  });

  // Fly to the picked country, or back to the world when it is cleared.
  let lastCountry = "";
  $effect(() => {
    const c = store.country;
    if (!ready || !map || c === lastCountry) return;
    lastCountry = c;
    const box = bounds.get(c);
    const narrow = innerWidth < 820;
    const padding = narrow ? 24 : { top: 48, bottom: 48, left: 48, right: 48 };
    if (box) map.fitBounds(box, { padding, maxZoom: 5.2, duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 900 });
    else if (!c) map.fitBounds(WORLD, { padding: 8, duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 700 });
  });

  function showTip(e: MapMouseEvent, title: string, lines: string[]) {
    tip = { x: e.point.x, y: e.point.y, title, lines };
  }

  function countryLines(iso: string) {
    const all = store.sources.filter((s) => s.countries.includes(iso));
    const here = store.filtered.filter((s) => s.countries.includes(iso));
    const t = store.tiers.get(iso) ?? 0;
    if (!all.length) return ["Not catalogued yet"];
    return [`Finest level: ${TIER_TEXT[t]}`,
      here.length === all.length ? plural(all.length, "source") : `${here.length} of ${plural(all.length, "source")} under these filters`];
  }

  function wire(m: MLMap) {
    m.on("mousemove", "country-fill", (e) => {
      const f = e.features?.[0] as MapGeoJSONFeature | undefined;
      const iso = f?.properties?.iso as string | undefined;
      if (hovered && hovered !== iso) m.setFeatureState({ source: "countries", id: hovered }, { hover: false });
      if (!iso) return;
      hovered = iso;
      m.setFeatureState({ source: "countries", id: iso }, { hover: true });
      m.getCanvas().style.cursor = store.catalogued.has(iso) ? "pointer" : "";
      if (!m.queryRenderedFeatures(e.point, { layers: ["farms"] }).length) showTip(e, store.placeName(iso), countryLines(iso));
    });
    m.on("mouseleave", "country-fill", () => {
      if (hovered) m.setFeatureState({ source: "countries", id: hovered }, { hover: false });
      hovered = null;
      tip = null;
      m.getCanvas().style.cursor = "";
    });
    m.on("mousemove", "farms", (e) => {
      const p = e.features?.[0]?.properties;
      if (!p) return;
      m.getCanvas().style.cursor = "pointer";
      const src = store.byId.get(p.entry);
      showTip(e, p.name, [plural(p.units, "unit"), src ? src.publisher : p.entry,
        p.matched ? "Location matched by name, not reviewed" : "Location from the publisher's register"]);
    });
    m.on("click", (e) => {
      const farm = m.queryRenderedFeatures(e.point, { layers: ["farms"] })[0];
      if (farm) {
        const src = store.byId.get(farm.properties.entry);
        store.go({ view: "map", country: src?.countries[0] ?? store.country, source: farm.properties.entry });
        return;
      }
      const f = m.queryRenderedFeatures(e.point, { layers: ["country-fill"] })[0];
      const iso = f?.properties?.iso as string | undefined;
      if (iso && store.catalogued.has(iso)) store.go({ country: store.country === iso && !store.source ? "" : iso, source: "" });
    });
  }

  function toggleGlobe() {
    globe = !globe;
    map?.setProjection({ type: globe ? "globe" : "mercator" });
  }

  onMount(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetch("./data/countries.geojson");
        outlines = await res.json();
      } catch {
        failed = "The country outlines could not be loaded.";
        return;
      }
      for (const f of outlines!.features) if (f.properties?.iso) bounds.set(f.properties.iso, mainBox(f.geometry));
      if (!alive) return;
      const m = new maplibregl.Map({
        container: host, style: dark() ? STYLE.dark : STYLE.light, bounds: WORLD,
        fitBoundsOptions: { padding: 8 }, minZoom: 0, maxZoom: 11, renderWorldCopies: false,
        attributionControl: { compact: true, customAttribution: "Outlines: Natural Earth. Farms: OpenStreetMap (ODbL), REPD (OGL), Danish Energy Agency, US EIA, BNetzA MaStR (dl-de/by-2-0) and the data publishers" },
        dragRotate: false, pitchWithRotate: false, touchPitch: false,
      });
      map = m;
      m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      m.on("style.load", addLayers);
      m.once("load", () => host.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show"));
      m.on("error", (e: ErrorEvent) => { if (!ready) failed = `The basemap did not load (${e.error?.message ?? "network"}).`; });
      wire(m);
    })();

    // Follow the theme: swap the basemap and re-add the data layers on top.
    const swap = () => {
      if (!map) return;
      ready = false;
      map.setStyle(dark() ? STYLE.dark : STYLE.light, { diff: false });
    };
    const mq = matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", swap);
    const mo = new MutationObserver(swap);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      alive = false;
      mq.removeEventListener("change", swap);
      mo.disconnect();
      map?.remove();
    };
  });

  let counts = $derived.by(() => {
    const c = [0, 0, 0, 0, 0];
    for (const iso of store.catalogued) c[store.tiers.get(iso) ?? 0] += 1;
    return c;
  });
  const pickTier = (t: number) => store.set("level", store.level === `tier:${t}` ? "" : `tier:${t}`);
</script>

<div class="map-wrap">
  <div class="map" bind:this={host} role="img" aria-label="World map shaded by the finest level of observed wind data each country publishes. Use the country list for keyboard access."></div>

  {#if tip}
    <div class="tip" style:left="{tip.x}px" style:top="{tip.y}px" role="presentation">
      <strong>{tip.title}</strong>
      {#each tip.lines as l (l)}<span>{l}</span>{/each}
    </div>
  {/if}

  {#if failed}<p class="map-state">{failed} The lists and tables still work.</p>{/if}

  <div class="legend" class:open={keyOpen} aria-label="Map key">
    <button type="button" class="lg-toggle" aria-expanded={keyOpen} onclick={() => (keyOpen = !keyOpen)}>Key</button>
    <p class="lg-title">Finest level published</p>
    <ul>
      {#each [1, 2, 3, 4] as t (t)}
        <li>
          <button type="button" class:on={store.level === `tier:${t}`} aria-pressed={store.level === `tier:${t}`} onclick={() => pickTier(t)}>
            <LevelDot tier={t} size={12} /><span>{TIER_TEXT[t]}</span><b class="num">{counts[t]}</b>
          </button>
        </li>
      {/each}
      {#if counts[0]}<li class="muted"><LevelDot tier={0} size={12} /><span>None under these filters</span><b class="num">{counts[0]}</b></li>{/if}
      {#if store.farms?.farms.length}<li class="muted"><i class="farm" aria-hidden="true"></i><span title="Units whose own output is published and whose location is known. So far: {located}">Farm or turbine with its own output</span><b class="num">{store.farms.farms.length}</b></li>{/if}
    </ul>
  </div>

  <button type="button" class="proj" onclick={toggleGlobe} aria-pressed={globe} title={globe ? "Show a flat map" : "Show a globe"}>
    <Icon name={globe ? "flat" : "globe"} />{globe ? "Flat" : "Globe"}
  </button>
</div>

<style>
  .map-wrap { position: relative; min-height: 0; height: 100%; background: var(--surface-3); }
  .map { position: absolute; inset: 0; }
  .tip {
    position: absolute; z-index: 3; pointer-events: none; transform: translate(12px, 12px);
    display: grid; gap: 1px; min-width: 160px; max-width: 260px; padding: 8px 10px;
    background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
    box-shadow: var(--shadow-2); font-size: 12.5px; color: var(--ink-2);
  }
  .tip strong { color: var(--ink); font-size: 13.5px; font-weight: 600; }
  .map-state { position: absolute; top: 16px; left: 16px; right: 16px; padding: 10px 12px; background: var(--surface);
    border-radius: var(--radius); box-shadow: var(--shadow-1); font-size: 13px; }
  .legend {
    position: absolute; left: 12px; bottom: 28px; z-index: 2; padding: 10px 6px 6px;
    background: color-mix(in srgb, var(--surface) 94%, transparent); border: 1px solid var(--line);
    border-radius: var(--radius); box-shadow: var(--shadow-1); font-size: 12.5px; min-width: 220px;
  }
  .lg-title { padding: 0 8px 4px; font-weight: 600; color: var(--ink); }
  .lg-toggle { display: none; }
  ul { list-style: none; margin: 0; padding: 0; }
  li > button, li.muted {
    display: grid; grid-template-columns: 12px 1fr auto; align-items: center; gap: 8px; width: 100%;
    padding: 4px 8px; border: 0; background: none; text-align: left; border-radius: var(--radius-sm); color: var(--ink-2);
  }
  li > button:hover { background: var(--surface-3); color: var(--ink); }
  li > button.on { background: var(--accent-wash); color: var(--ink); }
  li b { font-weight: 600; color: var(--ink); }
  li.muted { color: var(--ink-3); }
  .farm { width: 9px; height: 9px; margin: 0 1.5px; border-radius: 50%; background: var(--farm); box-shadow: 0 0 0 1.5px var(--surface); }
  .proj {
    position: absolute; top: 84px; right: 10px; z-index: 2; display: inline-flex; align-items: center; gap: 5px;
    height: 29px; padding: 0 9px; background: var(--surface); border: 0; border-radius: 4px;
    box-shadow: 0 0 0 2px rgb(0 0 0 / 0.1); font-size: 12.5px; font-weight: 500;
  }
  .map-wrap :global(.maplibregl-ctrl-attrib) { font-size: 11px; }
  @media (max-width: 819px) {
    .legend { left: 8px; top: 8px; bottom: auto; min-width: 0; padding: 2px; font-size: 12px; }
    .proj { top: 76px; }
    .lg-title { display: none; }
    .lg-toggle { display: block; height: 28px; padding: 0 10px; border: 0; background: none; font-weight: 600; font-size: 12.5px; }
    .legend:not(.open) ul { display: none; }
    .legend.open { padding: 2px 2px 6px; }
  }
</style>
