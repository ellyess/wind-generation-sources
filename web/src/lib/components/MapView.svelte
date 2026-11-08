<script lang="ts">
  import * as maplibregl from "maplibre-gl";
  import type { ErrorEvent, ExpressionSpecification, GeoJSONSource, Map as MLMap, MapGeoJSONFeature, MapMouseEvent } from "maplibre-gl";
  import type * as GeoJSON from "geojson";
  import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

  maplibregl.setWorkerUrl(workerUrl);
  import { onMount } from "svelte";
  import { store } from "../store.svelte";
  import { TIER_TEXT, plural } from "../text";
  import { PLACED, mwText } from "./FarmTable.svelte";
  import Icon from "./Icon.svelte";
  import LevelDot from "./LevelDot.svelte";

  // OpenFreeMap's dark style, recoloured on load to the site palette (restyleBase).
  const STYLE = "https://tiles.openfreemap.org/styles/dark";
  const WORLD: [number, number, number, number] = [-168, -50, 178, 72];
  // Locations matched to units by name (crosswalk/build.py); the rest come from the publisher.
  const MATCHED = new Set(["osm", "repd", "wikidata"]);
  // GB stations with no confident farm match, placed at their postcode's centroid (crosswalk/lists.py).
  const POSTCODE = "os-codepoint-open";
  const sizedCount = $derived((store.farms?.farms ?? []).filter((f) => f.mw != null).length);
  const approxCount = $derived((store.farms?.farms ?? []).filter((f) => f.located_by === POSTCODE).length);
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
  const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

  /**
   * Circle radius by zoom. A farm with a capacity scales with sqrt(MW) (so area tracks capacity),
   * clamped so a small farm stays visible and a 1 GW offshore farm does not cover a country; one
   * without keeps the old fixed size. Turbine-register points stay small and vary only mildly.
   * At zoom 6: 10 MW is 3.3 px, 100 MW 6 px, 1 GW 14 px (the cap).
   */
  const SIZE: [zoom: number, plain: number, base: number, perRootMW: number, lo: number, hi: number, turbine: number][] = [
    [2, 2.2, 1.4, 0.12, 1.2, 6, 0.8],
    [6, 4.5, 2, 0.4, 2, 14, 1.8],
    [10, 7, 3, 0.8, 3.5, 26, 4.5],
  ];
  function radius(extra = 0): ExpressionSpecification {
    const mw: ExpressionSpecification = ["get", "mw"];
    const root: ExpressionSpecification = ["sqrt", mw];
    const stops = SIZE.flatMap(([z, plain, base, k, lo, hi, turb]) => [z, ["+", extra, ["case",
      ["get", "turbine"], ["case", [">", mw, 0], ["*", turb, ["min", 1.5, ["max", 0.6, ["+", 0.6, ["*", 0.2, root]]]]], turb],
      [">", mw, 0], ["min", hi, ["max", lo, ["+", base, ["*", k, root]]]],
      plain]]]);
    return ["interpolate", ["linear"], ["zoom"], ...stops] as ExpressionSpecification;
  }
  // A point without a capacity draws about as large as a 50 MW farm, so it sorts like one.
  const sizeOf = (mw: number) => (mw > 0 ? mw : 50);
  /** The smallest of the farm points under the pointer: the one drawn on top. */
  const topFarm = (fs: MapGeoJSONFeature[]) => fs.reduce<MapGeoJSONFeature | undefined>((best, f) =>
    !best || sizeOf(f.properties.mw) < sizeOf(best.properties.mw) ? f : best, undefined);
  const focusFilter = (): ExpressionSpecification => ["==", ["id"], store.focusFarm ?? -1];

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

  /** Flatten the basemap to the site palette: sage land, charcoal sea, dark borders, quiet labels. */
  function restyleBase(m: MLMap) {
    const land = css("--land"), sea = css("--sea"), border = css("--land-line"), label = css("--map-label");
    for (const l of m.getStyle().layers) {
      const sl = (l as { "source-layer"?: string })["source-layer"] ?? "";
      const set = (k: string, v: unknown) => m.setPaintProperty(l.id, k as never, v as never);
      if (l.type === "background") set("background-color", land);
      else if (sl === "water") set("fill-color", sea);
      else if (sl === "waterway") set("line-color", sea);
      else if (sl === "landcover" || sl === "landuse" || sl === "aeroway") m.setLayoutProperty(l.id, "visibility", "none");
      else if (sl === "building") { set("fill-color", "#36443f"); set("fill-outline-color", "#36443f"); }
      else if (sl === "transportation" && l.type === "line") { set("line-color", "#4b5a55"); }
      else if (sl === "boundary") { set("line-color", l.id.startsWith("boundary_country") ? border : "#33403b"); set("line-blur", 0); }
      else if (l.type === "symbol") {
        set("text-color", sl === "water_name" ? "#56645f" : l.id.startsWith("place_country") ? "#c3cfca" : label);
        set("text-halo-color", sl === "water_name" ? "rgba(0,0,0,0)" : "rgba(26,30,33,0.7)");
        set("text-halo-width", 1); set("text-halo-blur", 0.5);
      }
    }
  }

  function addLayers() {
    if (!map || !outlines) return;
    const m = map;
    restyleBase(m);
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
          1, ["case", ["boolean", ["feature-state", "cat"], false], 0.8, 0],
          5, ["case", ["boolean", ["feature-state", "cat"], false], 0.55, 0],
          8, ["case", ["boolean", ["feature-state", "cat"], false], 0.4, 0]],
      } }, before);
    m.addLayer({ id: "country-hover", type: "line", source: "countries",
      paint: { "line-color": css("--ink"), "line-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.55, 0],
        "line-width": 1 } });
    m.addLayer({ id: "country-picked", type: "line", source: "countries",
      paint: { "line-color": css("--ink"), "line-opacity": ["case", ["boolean", ["feature-state", "picked"], false], 1, 0],
        "line-width": 2 } });
    m.addSource("farms", { type: "geojson", data: farmData() });
    m.addLayer({ id: "farms", type: "circle", source: "farms",
      // Big circles first, so the small ones drawn over them stay visible and clickable.
      layout: { "circle-sort-key": ["get", "sort"] },
      paint: {
        // Postcode centroids are approximate: drawn as hollow rings, not filled dots.
        "circle-color": ["case", ["get", "approx"], css("--sea"), css("--farm")],
        // Single turbines (Denmark's and Germany's registers) draw smaller so a dense fleet does not hide the country.
        "circle-radius": radius(),
        "circle-stroke-color": ["case", ["get", "approx"], css("--farm"), css("--sea")],
        "circle-stroke-width": ["interpolate", ["linear"], ["zoom"],
          2, ["case", ["get", "approx"], 1, ["get", "turbine"], 0, 0.6],
          8, ["case", ["get", "approx"], 1.8, ["get", "turbine"], 0.8, 1.5]],
        "circle-opacity": ["case", ["boolean", ["get", "shown"], true], 1, 0.15],
        "circle-stroke-opacity": ["case", ["boolean", ["get", "shown"], true], 1, 0.15],
      } });
    // The farm picked in the panel's table: an ink ring around its point.
    m.addLayer({ id: "farm-focus", type: "circle", source: "farms", filter: focusFilter(),
      paint: { "circle-radius": radius(3), "circle-color": "rgba(0,0,0,0)",
        "circle-stroke-color": css("--ink"), "circle-stroke-width": 2 } });
    paint();
    ready = true;
  }

  /** The open source's countries, outlined and framed while it is open. */
  let srcCountries = $derived(store.source ? store.byId.get(store.source)?.countries ?? [] : []);

  function farmData(): GeoJSON.FeatureCollection {
    // With a source open, only its own farms stay at full strength.
    const shown = new Set(store.source && store.byId.has(store.source) ? [store.source] : store.filtered.map((s) => s.id));
    return { type: "FeatureCollection", features: (store.farms?.farms ?? []).map((f, i) => {
      const on = shown.has(f.entry), mw = f.mw ?? 0;
      return {
        type: "Feature", id: i, geometry: { type: "Point", coordinates: [f.lon, f.lat] },
        properties: { name: f.name, entry: f.entry, units: f.n, shown: on, mw, placed: f.located_by,
          turbine: !!f.turbine, matched: MATCHED.has(f.located_by), approx: f.located_by === POSTCODE,
          // Faded points sit under every shown one; within each, larger under smaller.
          sort: (on ? 0 : -1e5) - sizeOf(mw) },
      };
    }) };
  }

  function paint() {
    if (!map || !outlines || !map.getSource("countries")) return;
    for (const f of outlines.features) {
      const iso = f.properties?.iso;
      if (!iso) continue;
      map.setFeatureState({ source: "countries", id: iso }, {
        tier: store.tiers.get(iso) ?? 0,
        cat: store.catalogued.has(iso),
        picked: store.country === iso || (!store.country && srcCountries.includes(iso)),
      });
    }
    (map.getSource("farms") as GeoJSONSource | undefined)?.setData(farmData());
  }

  // Repaint when filters or the pick change, or when the farm points arrive after the map.
  $effect(() => {
    void store.tiers; void store.country; void store.filtered; void store.farms; void store.source;
    paint();
  });

  // Fly to the picked country, or to an open source's countries, or back to the world.
  let lastFrame = "";
  const ownCountries = (c: string) => (!c && srcCountries.length && srcCountries.length <= 6 ? srcCountries : []);
  const frameKey = () => store.country || ownCountries(store.country).join(",");
  $effect(() => {
    const c = store.country;
    const own = ownCountries(c);
    const key = c || own.join(",");
    if (!ready || !map || key === lastFrame) return;
    lastFrame = key;
    const boxes = (c ? [c] : own).map((k) => bounds.get(k)).filter((b) => !!b);
    const narrow = innerWidth < 820;
    const padding = narrow ? 24 : { top: 48, bottom: 48, left: 48, right: 48 };
    if (boxes.length) {
      const box: [number, number, number, number] = [Math.min(...boxes.map((b) => b[0])), Math.min(...boxes.map((b) => b[1])),
        Math.max(...boxes.map((b) => b[2])), Math.max(...boxes.map((b) => b[3]))];
      map.fitBounds(box, { padding, maxZoom: 5.2, duration: still() ? 0 : 900 });
    } else if (!key) map.fitBounds(WORLD, { padding: 8, duration: still() ? 0 : 700 });
  });

  // Fly to the farm picked in the table and ring it.
  $effect(() => {
    const id = store.focusFarm;
    if (!ready || !map) return;
    map.setFilter("farm-focus", focusFilter());
    const f = id == null ? undefined : store.farms?.farms[id];
    if (!f) return;
    map.flyTo({ center: [f.lon, f.lat], zoom: Math.max(map.getZoom(), f.turbine ? 10 : 8), duration: still() ? 0 : 900 });
    // On phones the map sits above the panel; bring it into view.
    if (innerWidth < 820 && host.getBoundingClientRect().bottom < 80) host.scrollIntoView({ behavior: still() ? "auto" : "smooth" });
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
      const top = topFarm(e.features ?? []);
      const p = top?.properties;
      if (!p) return;
      m.getCanvas().style.cursor = "pointer";
      if (store.hoverFarm !== top.id) store.hoverFarm = top.id as number;
      const src = store.byId.get(p.entry);
      const via = PLACED[p.placed]?.via;
      showTip(e, p.name, [p.mw > 0 ? `${mwText(p.mw)} MW, ${plural(p.units, "unit")}` : plural(p.units, "unit"),
        src ? src.publisher : p.entry,
        p.approx ? "Approximate: placed at the station's postcode centroid, not at the turbine"
          : p.placed === "wikidata" ? "Location linked by unit ID on Wikidata, not reviewed"
          : p.matched ? `Location matched by name${via ? ` (${via})` : ""}, not reviewed` : "Location from the publisher's register"]);
    });
    m.on("mouseleave", "farms", () => { store.hoverFarm = null; });
    m.on("click", (e) => {
      const farm = topFarm(m.queryRenderedFeatures(e.point, { layers: ["farms"] }));
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

  /** "zoom/lat/lon" from the address, as a camera. */
  function place(pos: string) {
    const [z, lat, lon] = pos.split("/").map(Number);
    return pos && [z, lat, lon].every(Number.isFinite) ? { zoom: z, center: [lon, lat] as [number, number] } : null;
  }
  // Write the position into the address once the map settles, replacing the entry rather than
  // adding one, so panning never floods the history.
  let keepTimer: ReturnType<typeof setTimeout> | undefined;
  function keep() {
    clearTimeout(keepTimer);
    keepTimer = setTimeout(() => {
      if (!map || store.view !== "map") return;
      const c = map.getCenter();
      store.pos = `${map.getZoom().toFixed(2)}/${c.lat.toFixed(4)}/${c.lng.toFixed(4)}`;
      history.replaceState(history.state, "", store.url());
    }, 250);
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
      // A position in the address wins over flying to the picked country.
      const at = place(store.pos);
      if (at) lastFrame = frameKey();
      const m = new maplibregl.Map({
        container: host, style: STYLE,
        ...(at ?? { bounds: WORLD, fitBoundsOptions: { padding: 8 } }), minZoom: 0, maxZoom: 11, renderWorldCopies: false,
        attributionControl: { compact: true, customAttribution: "Outlines: Natural Earth. Farms: OpenStreetMap (ODbL), REPD (OGL), postcode centroids: Contains OS data © Crown copyright and database right 2026, Contains Royal Mail data © Royal Mail copyright and database right 2026, Contains National Statistics data © Crown copyright and database right 2026 (OS Code-Point Open, OGL), Danish Energy Agency, US EIA, BNetzA MaStR (dl-de/by-2-0) and the data publishers" },
        dragRotate: false, pitchWithRotate: false, touchPitch: false,
        // On touch screens the page scrolls with one finger; the map pans with two.
        cooperativeGestures: matchMedia("(pointer: coarse)").matches,
      });
      map = m;
      m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      m.on("style.load", addLayers);
      m.once("load", () => host.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show"));
      m.on("error", (e: ErrorEvent) => { if (!ready) failed = `The basemap did not load (${e.error?.message ?? "network"}).`; });
      wire(m);
      m.on("moveend", keep);
    })();

    // Back and Forward restore the position each history entry had.
    const pop = () => {
      const at = place(store.pos);
      if (!at || !map) return;
      lastFrame = frameKey();
      map.jumpTo(at);
    };
    addEventListener("popstate", pop);

    return () => {
      alive = false;
      clearTimeout(keepTimer);
      removeEventListener("popstate", pop);
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
      {#if store.farms?.farms.length}<li class="muted"><i class="farm" aria-hidden="true"></i><span title="Units whose own output is published and whose location is known. So far: {located}">Farm or turbine with its own output</span><b class="num">{store.farms.farms.length - approxCount}</b></li>{/if}
      {#if sizedCount}<li class="muted"><i class="sizes" aria-hidden="true"><i></i><i></i></i><span title="Circle area grows with the capacity behind the point; points with no published capacity keep a middle size">Larger circle, more capacity</span><b></b></li>{/if}
      {#if approxCount}<li class="muted"><i class="farm approx" aria-hidden="true"></i><span title="Great Britain stations with no confident farm match, placed at their postcode's centroid (Ordnance Survey Code-Point Open), not at the turbine">Approximate: at its postcode centroid</span><b class="num">{approxCount}</b></li>{/if}
    </ul>
  </div>

  <button type="button" class="proj" onclick={toggleGlobe} aria-pressed={globe} title={globe ? "Show a flat map" : "Show a globe"}>
    <Icon name={globe ? "flat" : "globe"} />{globe ? "Flat" : "Globe"}
  </button>
</div>

<style>
  .map-wrap { position: relative; min-height: 0; height: 100%; background: var(--sea); }
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
  .farm.approx { background: var(--surface); box-shadow: inset 0 0 0 1.5px var(--farm); }
  .sizes { position: relative; display: block; width: 12px; height: 12px; }
  .sizes i { position: absolute; bottom: 0; border-radius: 50%; background: var(--farm); box-shadow: 0 0 0 1px var(--surface); }
  .sizes i:first-child { left: 0; width: 11px; height: 11px; }
  .sizes i:last-child { right: -1px; width: 5px; height: 5px; }
  .proj {
    position: absolute; top: 84px; right: 10px; z-index: 2; display: inline-flex; align-items: center; gap: 5px;
    height: 29px; padding: 0 9px; background: var(--surface); border: 0; border-radius: 4px;
    box-shadow: 0 0 0 2px rgb(0 0 0 / 0.1); font-size: 12.5px; font-weight: 500;
  }
  .map-wrap :global(.maplibregl-ctrl-attrib) { font-size: 11px; }
  /* MapLibre's own controls, in the site palette. */
  .map-wrap :global(.maplibregl-ctrl-group) { background: var(--surface); box-shadow: var(--shadow-1); border: 1px solid var(--line); }
  .map-wrap :global(.maplibregl-ctrl-group button + button) { border-top-color: var(--line); }
  .map-wrap :global(.maplibregl-ctrl-group button:not(:disabled):hover) { background: var(--surface-3); }
  .map-wrap :global(.maplibregl-ctrl-icon) { filter: invert(1) brightness(0.85); }
  .map-wrap :global(.maplibregl-ctrl-attrib) { background: color-mix(in srgb, var(--surface) 85%, transparent); color: var(--ink-3); }
  .map-wrap :global(.maplibregl-ctrl-attrib a) { color: var(--ink-2); }
  .map-wrap :global(.maplibregl-ctrl-attrib-button) { background-color: var(--surface); filter: invert(1) brightness(0.85); }
  .map-wrap :global(.maplibregl-cooperative-gesture-screen) { background: color-mix(in srgb, var(--bg) 80%, transparent); color: var(--ink); }
  @media (max-width: 819px) {
    .legend { left: 8px; top: 8px; bottom: auto; min-width: 0; padding: 2px; font-size: 12px; }
    .proj { top: 76px; }
    .lg-title { display: none; }
    .lg-toggle { display: block; height: 28px; padding: 0 10px; border: 0; background: none; font-weight: 600; font-size: 12.5px; }
    .legend:not(.open) ul { display: none; }
    .legend.open { padding: 2px 2px 6px; }
  }
</style>
