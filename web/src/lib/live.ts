// Live previews, fetched in the visitor's browser from publishers that allow it (CORS) and need
// no key. Nothing is stored or re-hosted by the catalogue. Energinet is absent: its API returns an
// empty body to cross-origin requests.

export interface Point { t: Date; v: number }
export interface Series {
  points: Point[];
  unit: string;        // what v is: "MW" (average power) or "GWh" (energy per bar)
  kind: "line" | "bars";
  stepText: string;
  request: string;     // the URL a reader can open to see the raw response
  note?: string;
}

const DAY = 86400_000;
const iso = (d: Date) => d.toISOString().slice(0, 10);
const cache = new Map<string, Promise<Series>>();

async function json(url: string, init?: RequestInit) {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`${res.status === 429 ? "rate limited" : `HTTP ${res.status}`} from ${new URL(url).host}`);
  return res.json();
}

const sorted = (pts: Point[]) => pts.filter((p) => Number.isFinite(p.v)).sort((a, b) => +a.t - +b.t);

const ADAPTERS: Record<string, () => Promise<Series>> = {
  "gb-elexon-bmrs-fuel-type": async () => {
    const now = new Date();
    const url = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH?"
      + `settlementDateFrom=${iso(new Date(+now - 7 * DAY))}&settlementDateTo=${iso(now)}&fuelType=WIND&format=json`;
    const d = await json(url);
    const seen = new Map<string, Point>();
    for (const r of d.data) seen.set(r.startTime, { t: new Date(r.startTime), v: r.generation });
    return { points: sorted([...seen.values()]), unit: "MW", kind: "line", stepText: "30 min",
      request: url, note: "FUELHH wind, average MW per settlement period." };
  },
  "fr-rte-eco2mix-national": async () => {
    const url = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-tr/exports/json?"
      + new URLSearchParams({ select: "date_heure,eolien", where: "date_heure>=now(days=-7) and eolien is not null",
        order_by: "date_heure" });
    const d: { date_heure: string; eolien: number }[] = await json(url);
    return { points: sorted(d.map((r) => ({ t: new Date(r.date_heure), v: r.eolien }))), unit: "MW",
      kind: "line", stepText: "15 min", request: url, note: "éCO2mix real-time wind, MW." };
  },
  "be-elia-wind-production": async () => {
    const url = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods031/exports/json?"
      + new URLSearchParams({ select: "datetime,sum(measured) as mw,count(measured) as n", group_by: "datetime",
        where: "datetime>=now(days=-7)", order_by: "datetime" });
    const d: { datetime: string; mw: number; n: number }[] = await json(url);
    // The newest quarter-hours can arrive before every region has reported; a partial sum reads low, so drop them.
    const full = [...d.map((r) => r.n)].sort((a, b) => a - b)[Math.floor(d.length / 2)] ?? 0;
    let end = d.length;
    while (end > 0 && d[end - 1].n < full) end--;
    return { points: sorted(d.slice(0, end).map((r) => ({ t: new Date(r.datetime), v: r.mw }))), unit: "MW", kind: "line",
      stepText: "15 min", request: url, note: "Measured wind summed over every region and grid row; trailing quarter-hours with regions still missing are left out." };
  },
  "de-smard": async () => {
    const sum = new Map<number, number>();
    const seen = new Map<number, number>();
    let request = "";
    for (const filt of [4067, 1225]) {
      const base = `https://www.smard.de/app/chart_data/${filt}/DE/`;
      const stamps: number[] = (await json(`${base}index_quarterhour.json`)).timestamps;
      for (const ts of stamps.slice(-2)) {
        const url = `${base}${filt}_DE_quarterhour_${ts}.json`;
        if (!request) request = url;
        const series: [number, number | null][] = (await json(url)).series;
        for (const [t, v] of series) if (v != null) { sum.set(t, (sum.get(t) ?? 0) + v); seen.set(t, (seen.get(t) ?? 0) + 1); }
      }
    }
    const cut = Date.now() - 7 * DAY;
    // SMARD gives MWh per quarter hour; times four is average MW.
    // Keep only quarter-hours both series have published, so the newest point is not onshore alone.
    const points = [...sum].filter(([t]) => t >= cut && seen.get(t) === 2).map(([t, v]) => ({ t: new Date(t), v: v * 4 }));
    return { points: sorted(points), unit: "MW", kind: "line", stepText: "15 min", request,
      note: "Onshore (filter 4067) plus offshore (1225), MWh per quarter hour times four." };
  },
  "es-ree-redata": async () => {
    const end = new Date();
    const start = new Date(+end - 30 * DAY);
    const url = "https://apidatos.ree.es/en/datos/generacion/estructura-generacion?"
      + `start_date=${iso(start)}T00:00&end_date=${iso(end)}T23:59&time_trunc=day`;
    const d = await json(url);
    const wind = d.included.find((i: { attributes: { title: string } }) => i.attributes.title === "Wind");
    if (!wind) throw new Error("no Wind series in the response");
    const points = wind.attributes.values.map((v: { datetime: string; value: number }) =>
      // Each value is a Spanish calendar day; keep its date, whatever the offset, so it labels in UTC.
      ({ t: new Date(`${v.datetime.slice(0, 10)}T00:00:00Z`), v: v.value / 1000 }));
    return { points: sorted(points), unit: "GWh", kind: "bars", stepText: "daily", request: url,
      note: "The hourly widget is often unavailable, so this shows daily energy." };
  },
};

export const hasLive = (id: string) => id in ADAPTERS;
export const liveIds = Object.keys(ADAPTERS);

export function fetchLive(id: string): Promise<Series> {
  let p = cache.get(id);
  if (!p) {
    p = ADAPTERS[id]();
    p.catch(() => cache.delete(id));
    cache.set(id, p);
  }
  return p;
}

// Eurostat annual gross wind production and net capacity, for the country view.
// Eurostat uses EL for Greece and UK for the United Kingdom.
const EUROSTAT_GEO: Record<string, string> = { GR: "EL", GB: "UK" };
export interface AnnualPoint { year: number; gwh: number; mw?: number; cf?: number }
export interface Annual { points: AnnualPoint[]; request: string; capacityRequest: string }
const annualCache = new Map<string, Promise<Annual>>();
const EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/";

function byYear(d: any): Map<number, number> {
  const idx: Record<string, number> = d.dimension.time.category.index;
  const out = new Map<number, number>();
  for (const [year, i] of Object.entries(idx)) {
    const v = d.value[String(i)];
    if (v != null) out.set(Number(year), v as number);
  }
  return out;
}

const hours = (y: number) => ((y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 8784 : 8760);

export function fetchEurostat(code: string): Promise<Annual> {
  let p = annualCache.get(code);
  if (!p) {
    const geo = EUROSTAT_GEO[code] ?? code;
    const url = `${EUROSTAT}nrg_bal_peh?geo=${geo}&siec=RA300&nrg_bal=GEP&unit=GWH&lang=en`;
    const capUrl = `${EUROSTAT}nrg_inf_epcrw?geo=${geo}&siec=RA300&plant_tec=CAP_NET_ELC&unit=MW&lang=en`;
    p = Promise.all([json(url), json(capUrl).catch(() => null)]).then(([gen, cap]) => {
      const g = byYear(gen), c = cap ? byYear(cap) : new Map<number, number>();
      const points = [...g].sort((a, b) => a[0] - b[0]).map(([year, gwh]) => {
        const mw = c.get(year);
        // Capacity is counted at year end; average it with the year before so a fleet that grew
        // during the year is not divided by capacity it only had in December.
        const prev = c.get(year - 1);
        // A fleet that grew by more than half in a year makes even the mean a poor denominator.
        const steady = mw != null && prev != null && prev > 0 && mw / prev <= 1.5;
        const mean = steady ? (mw + prev) / 2 : undefined;
        const cf = mean && mean > 0 && gwh > 0 ? (gwh * 1000) / (mean * hours(year)) : undefined;
        return { year, gwh, mw, cf: cf != null && cf < 1 ? cf : undefined };
      });
      return { points, request: url, capacityRequest: capUrl };
    });
    p.catch(() => annualCache.delete(code));
    annualCache.set(code, p);
  }
  return p;
}
