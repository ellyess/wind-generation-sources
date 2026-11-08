import type { Catalogue, Checks, Farms, Source } from "./types";
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
  }

  set(key: FilterKey, value: string) {
    this[key] = value;
  }

  readURL() {
    const p = new URLSearchParams(location.search);
    const v = p.get("view") as View | null;
    this.view = v && VIEWS.includes(v) ? v : "map";
    this.country = p.get("country") ?? "";
    this.source = p.get("source") ?? "";
    this.focusFarm = null;
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

  /** Navigation that should be undone with Back: views, countries, sources. */
  go(patch: Partial<{ view: View; country: string; source: string }>) {
    if (patch.view !== undefined) this.view = patch.view;
    if (patch.country !== undefined) this.country = patch.country;
    if (patch.source !== undefined) this.source = patch.source;
    this.focusFarm = null;
    history.pushState(null, "", this.url());
  }
}

export const store = new Store();
export { CONTINENTS, LEVELS };

export async function load() {
  const base = "./data/";
  try {
    const res = await fetch(`${base}catalogue.json`, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    store.cat = await res.json();
  } catch (err) {
    store.error = (err as Error).message;
    return;
  }
  const extra = async (name: string) => {
    try {
      const r = await fetch(`${base}${name}`, { cache: "no-cache" });
      return r.ok ? r.json() : null;
    } catch {
      return null;
    }
  };
  const [checks, farms] = await Promise.all([extra("checks.json"), extra("farms.json")]);
  if (checks) store.checks = checks;
  if (farms) store.farms = farms;
}
