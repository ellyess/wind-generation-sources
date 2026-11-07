// Plain-English labels for every coded field. One place, so the map, table and charts agree.
export const LEVELS = ["turbine", "farm", "connection-point", "complex", "company", "zone", "country"];
export const STEPS = ["1s", "1min", "5min", "10min", "15min", "30min", "hourly", "daily", "monthly", "annual"];
export const CONTINENTS = ["Europe", "Americas", "Asia", "Oceania", "Africa"];

/** Finest-level tier: 1 turbine, 2 farm-like, 3 zone or company, 4 national. */
export const TIER: Record<string, number> = {
  turbine: 1, farm: 2, "connection-point": 2, complex: 2, company: 3, zone: 3, country: 4,
};
export const TIER_TEXT: Record<number, string> = {
  1: "Turbine", 2: "Farm or plant", 3: "Zone or company", 4: "National total", 0: "None catalogued",
};
export const TIER_LONG: Record<number, string> = {
  1: "Output per turbine", 2: "Output per farm, plant, complex or connection point",
  3: "Output per market zone, region or company", 4: "National total only", 0: "No source under these filters",
};

export const TEXT: Record<string, Record<string, string>> = {
  level: {
    turbine: "Turbine", farm: "Farm", "connection-point": "Connection point", complex: "Complex",
    company: "Company", zone: "Zone", country: "Country",
  },
  levelLong: {
    turbine: "Turbine", farm: "Farm",
    zone: "Zone (a market, balancing or reporting area)",
    complex: "Complex (several farms reported together)",
    "connection-point": "Connection point (output where it meets the grid)",
    company: "Company", country: "Country",
  },
  step: {
    "1s": "1 s", "1min": "1 min", "5min": "5 min", "10min": "10 min", "15min": "15 min",
    "30min": "30 min", hourly: "Hourly", daily: "Daily", monthly: "Monthly", annual: "Annual",
  },
  reuse: {
    allowed: "Allowed", "allowed-with-attribution": "Allowed with credit",
    "non-commercial-only": "Non-commercial only", "link-only": "Link only, no copies",
    prohibited: "Not allowed", unclear: "Unclear",
  },
  measure: {
    "metered-energy": "Metered energy", "reported-generation": "Reported generation",
    "estimated-generation": "Publisher's own estimate", "capacity-factor": "Capacity factor",
    certificates: "Certificates issued",
  },
  technology: {
    onshore: "Onshore", offshore: "Offshore",
    "onshore-and-offshore-split": "Onshore and offshore, reported separately",
    "onshore-and-offshore-combined": "Onshore and offshore, combined",
  },
  method: { api: "API", "bulk-download": "Bulk download", portal: "Web portal", request: "On request" },
  presence: {
    included: "Included", "separate-dataset": "In a separate dataset", none: "Not published",
    "not-applicable": "Not applicable",
  },
  curtailment: {
    reported: "Reported", "separate-dataset": "In a separate dataset",
    "not-reported": "Not reported", unknown: "Unknown",
  },
  status: { active: "Active", discontinued: "Discontinued", restricted: "Restricted" },
  role: {
    tso: "Transmission operator", "market-operator": "Market operator",
    "owner-operator": "Owner and operator", utility: "Utility", research: "Research body",
    "statistics-office": "Statistics office", government: "Government", aggregator: "Aggregator",
    "iso-rto": "Grid and market operator", regulator: "Regulator",
  },
};

/** Licence verdict to a status role, for the dot beside the words. */
export const REUSE_TONE: Record<string, string> = {
  allowed: "good", "allowed-with-attribution": "good", "non-commercial-only": "warn",
  "link-only": "serious", prohibited: "bad", unclear: "none",
};

export const REF_NAME: Record<string, string> = {
  "eu-eurostat-nrg-bal-peh": "Eurostat", "world-ember-monthly": "Ember",
};
export const BAND_TEXT: Record<string, string> = {
  agrees: "Within 15%", noted: "Within 30%", outside: "More than 30% away", small: "Too small to judge",
};
export const BAND_TONE: Record<string, string> = { agrees: "good", noted: "warn", outside: "bad", small: "none" };

export const fold = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function coverageText(cov: { start: number; end?: number }) {
  return cov.end ? `${cov.start}–${cov.end}` : `${cov.start} on`;
}

export function shortLink(url: string) {
  try {
    const u = new URL(url);
    const pyvwf = u.pathname.match(/^\/ellyess\/PyVWF\/blob\/[^/]+\/[^/]+\/(.+)$/);
    if (u.host === "github.com" && pyvwf) return `PyVWF audit: ${pyvwf[1]}`;
    let path = decodeURIComponent(u.pathname).replace(/\/$/, "");
    if (path.length > 40) path = `${path.slice(0, 38)}…`;
    return u.host.replace(/^www\./, "") + path;
  } catch {
    return url;
  }
}

export const twh = (v: number) => (v >= 10 ? v.toFixed(1) : v >= 1 ? v.toFixed(2) : v.toFixed(3));
export const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

// How to read a source's time stamps and values (the `conventions` block).
export const STAMP: Record<string, string> = {
  "period-start": "marks the start of each period", "period-end": "marks the end of each period",
  instant: "is an instantaneous reading", "period-label": "names the whole day, month or year", unknown: "is not documented",
};
export const VALUE: Record<string, string> = {
  "period-mean": "mean power over the period", "period-total": "total energy over the period",
  instantaneous: "instantaneous power", unknown: "not documented",
};
export function zoneText(z: string): string {
  if (z === "UTC") return "UTC";
  if (z === "not-applicable") return "No clock time (period labels)";
  if (z === "unknown") return "Not documented";
  if (z.startsWith("UTC")) return `${z}, all year`;
  return `${z.replace(/_/g, " ")} local time, with daylight saving`;
}
