import { tick } from "svelte";
import type { Catalogue, Checks, Farm, Farms, Source } from "./types";
import { CONTINENTS, LEVELS, STEPS, TIER, fold } from "./text";

export const REPO = "https://github.com/ellyess/wind-generation-sources";
export const VIEWS = ["map", "sources", "checks", "about"] as const;
export type View = (typeof VIEWS)[number];
// The map position in the address, as MapLibre writes it: #zoom/lat/lon.
const POS = /^\d+(\.\d+)?\/-?\d+(\.\d+)?\/-?\d+(\.\d+)?$/;
const FILTERS = ["level", "step", "reuse", "cap", "status", "review", "region", "q"] as const;
type FilterKey = (typeof FILTERS)[number];

// Codes the outlines file names oddly or not at all.
const FALLBACK_NAMES: Record<string, string> = { XK: "Kosovo" };

export type Indexed = Source & { _hay: string; _tier: number };

class Store {
  cat = $state<Catalogue | null>(null);
  checks = $state<Checks>({});
  farms = $state<Farms | null>(null);
  error = $state("");
  /** A farm point (its index in `farms.farms`) flown to from the table, and one hovered on the map. */
  focusFarm = $state<number | null>(null);
  /** Every point of the farm picked in the table, when it is drawn as several turbines. */
  focusGroup = $state<number[] | null>(null);
  hoverFarm = $state<number | null>(null);
  /** The map view as "zoom/lat/lon"; kept out of reactivity so panning does not re-run effects. */
  pos = "";

  view = $state<View>("map");
  country = $state("");
  source = $state("");
  level = $state("");
  step = $state("");
  reuse = $state("");
  cap = $state("");
  status = $state("");
  review = $state("");
  region = $state("");
  q = $state("");

  places = $derived(this.cat?.places ?? {});

  sources: Indexed[] = $derived.by(() => {
    const c = this.cat;
    if (!c) return [];
    return [...c.sources].sort((a, b) => a.id.localeCompare(b.id)).map((s) => ({
      ...s,
      _tier: TIER[s.level] ?? 4,
      _hay: fold([s.id, s.name, s.publisher, s.countries.join(" "), s.area, s.notes, s.licence.name,
        ...s.countries.map((k) => c.places[k]?.name ?? k),
        ...(s.traps ?? []).map((t) => `${t.summary} ${t.detail ?? ""}`)].filter(Boolean).join(" ")),
    }));
  });

  byId = $derived(new Map(this.sources.map((s) => [s.id, s])));

  /** Sources passing every filter except the country picked on the map. */
  filtered: Indexed[] = $derived(this.sources.filter((s) => this.matches(s)));

  /** The list the panel and table show: filters plus the picked country. */
  shown: Indexed[] = $derived(this.country
    ? this.filtered.filter((s) => s.countries.includes(this.country))
    : this.filtered);

  /** Finest tier per country under the filters. */
  tiers = $derived.by(() => {
    const m = new Map<string, number>();
    for (const s of this.filtered) for (const iso of s.countries) {
      const cur = m.get(iso);
      if (!cur || s._tier < cur) m.set(iso, s._tier);
    }
    return m;
  });

  catalogued = $derived(new Set(this.sources.flatMap((s) => s.countries)));

  activeFilters = $derived(FILTERS.filter((k) => this[k] !== "").length);

  continentOf = (code: string) => this.places[code]?.continent ?? "Elsewhere";
  placeName = (code: string) => this.places[code]?.name ?? FALLBACK_NAMES[code] ?? code;
  /** The country a farm point sits in. */
  farmCountry = (f: { entry: string; iso?: string }) => f.iso ?? this.byId.get(f.entry)?.countries[0] ?? "";

  matches(s: Indexed) {
    if (this.region && !s.countries.some((c) => this.continentOf(c) === this.region)) return false;
    if (this.level) {
      if (this.level.startsWith("tier:") ? s._tier !== Number(this.level.slice(5)) : s.level !== this.level) return false;
    }
    if (this.step && STEPS.indexOf(s.resolution) > STEPS.indexOf(this.step)) return false;
    if (this.status && s.status !== this.status) return false;
    if (this.cap === "included" && s.capacity !== "included") return false;
    if (this.cap === "any" && s.capacity === "none") return false;
    if (this.review === "reviewed" && s.reviewed === false) return false;
    if (this.review === "unreviewed" && s.reviewed !== false) return false;
    if (this.reuse) {
      const r = s.licence.redistribution;
      if (this.reuse === "open" ? !(r === "allowed" || r === "allowed-with-attribution") : r !== this.reuse) return false;
    }
    if (this.q) {
      const words = fold(this.q).split(/\s+/).filter(Boolean);
      if (!words.every((w) => s._hay.includes(w))) return false;
    }
    return true;
  }

  clearFilters() {
    for (const k of FILTERS) this[k] = "";
    // The button that called this goes away; give keyboard focus somewhere useful.
    void tick().then(() => (document.querySelector('input[type="search"]') as HTMLElement | null)?.focus());
  }

  set(key: FilterKey, value: string) {
    this[key] = value;
  }

  readURL() {
    const p = new URLSearchParams(location.search);
    const v = p.get("view") as View | null;
    this.view = v && VIEWS.includes(v) ? v : "map";
    this.country = (p.get("country") ?? "").toUpperCase();
    this.source = p.get("source") ?? "";
    this.focusFarm = null;
    this.focusGroup = null;
    for (const k of FILTERS) this[k] = p.get(k) ?? "";
    // The hash holds the map position; old links pointed at #<entry-id>.
    const hash = decodeURIComponent(location.hash.slice(1));
    this.pos = POS.test(hash) ? hash : "";
    if (hash && !this.pos && !this.source) this.source = hash;
  }

  url() {
    const p = new URLSearchParams();
    if (this.view !== "map") p.set("view", this.view);
    if (this.country) p.set("country", this.country);
    if (this.source) p.set("source", this.source);
    for (const k of FILTERS) if (this[k]) p.set(k, this[k]);
    const qs = p.toString();
    const pos = this.view === "map" && this.pos ? `#${this.pos}` : "";
    return `${location.pathname}${qs ? `?${qs}` : ""}${pos}`;
  }

  /** The address a navigation would lead to, for real links that can open in a new tab. */
  urlFor(patch: Partial<{ view: View; country: string; source: string }>) {
    const p = new URLSearchParams();
    const view = patch.view ?? this.view;
    const country = patch.country ?? this.country;
    const source = patch.source ?? this.source;
    if (view !== "map") p.set("view", view);
    if (country) p.set("country", country);
    if (source) p.set("source", source);
    for (const k of FILTERS) if (this[k]) p.set(k, this[k]);
    const qs = p.toString();
    return `${location.pathname}${qs ? `?${qs}` : ""}`;
  }

  /** href and click handler for an in-site link: a plain click stays in the page, a modified one opens a tab. */
  link(patch: Partial<{ view: View; country: string; source: string }>) {
    return {
      href: this.urlFor(patch),
      onclick: (e: MouseEvent) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
        e.preventDefault();
        this.go(patch);
      },
    };
  }

  /** Navigation that should be undone with Back: views, countries, sources. */
  go(patch: Partial<{ view: View; country: string; source: string }>) {
    if (patch.view !== undefined) this.view = patch.view;
    if (patch.country !== undefined) this.country = patch.country;
    if (patch.source !== undefined) this.source = patch.source;
    this.focusFarm = null;
    this.focusGroup = null;
    history.pushState(null, "", this.url());
  }
}

export const store = new Store();
export { CONTINENTS, LEVELS };

const base = "./data/";
const fetchData = async (name: string) => {
  try {
    const r = await fetch(`${base}${name}`, { cache: "no-cache" });
    return r.ok ? r.json() : null;
  } catch {
    return null;
  }
};

type FarmColumns = { licence: string; entries: string[]; located: string[]; count: number;
  cols: { name: string[]; entry: number[]; n: number[]; lat: number[]; lon: number[]; located_by: number[];
    turbine: number[]; mw: (number | null)[]; osm: (string | null)[]; iso: (string | null)[] } };
/** farms.json holds parallel columns to stay small; the site works with one object per point. */
function expandFarms(d: FarmColumns | Farms): Farms {
  if (!("cols" in d)) return d;
  const c = d.cols;
  const farms: Farm[] = new Array(d.count);
  for (let i = 0; i < d.count; i++) {
    const f: Farm = { name: c.name[i], entry: d.entries[c.entry[i]], n: c.n[i], lat: c.lat[i], lon: c.lon[i],
      located_by: d.located[c.located_by[i]] };
    if (c.turbine[i]) f.turbine = true;
    if (c.mw[i] != null) f.mw = c.mw[i]!;
    if (c.osm[i]) f.osm = c.osm[i]!;
    if (c.iso[i]) f.iso = c.iso[i]!;
    farms[i] = f;
  }
  return { licence: d.licence, farms };
}

let farmsLoading: Promise<void> | null = null;
/** The farm points are the largest file and only the map and its panels use them, so they load on demand. */
export function needFarms() {
  farmsLoading ??= fetchData("farms.json").then((f) => { if (f) store.farms = expandFarms(f); });
}

export async function load() {
  try {
    const res = await fetch(`${base}catalogue.json`, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    store.cat = await res.json();
  } catch (err) {
    store.error = (err as Error).message;
    return;
  }
  const checks = await fetchData("checks.json");
  if (checks) store.checks = checks;
}
