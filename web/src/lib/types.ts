export interface Trap { summary: string; detail?: string; evidence: string; found?: string; evidence_is_error?: boolean }
export interface Tool { name: string; url: string; language?: string }
export interface Source {
  id: string; name: string; publisher: string; publisher_role?: string;
  countries: string[]; area?: string; level: string; technology: string; measure: string;
  resolution: string;
  coverage: { start: number; end?: number; update?: string };
  capacity: string; coordinates: string; curtailment?: string;
  conventions?: { timezone: string; timestamp: string; unit: string; value: string; evidence: string; note?: string };
  access: { method: string; url: string; docs?: string; key_required: boolean; registration?: boolean;
    formats?: string[]; languages?: string[] };
  licence: { name: string; url?: string; spdx?: string; redistribution: string; attribution?: string;
    verified: boolean; note?: string };
  traps?: Trap[]; tools?: Tool[]; notes?: string; status: string; reviewed?: boolean;
  last_checked: string; checked_by?: string; snippet?: boolean;
}
export interface Place { name: string; continent: string }
export interface Catalogue { generated: string; count: number; countries: string[];
  places: Record<string, Place>; sources: Source[] }
export interface LinkRow { ok: number; total: number; broken: { url: string; role: string }[];
  recheck: { url: string; role: string }[]; unchecked: { url: string; role: string }[] }
export interface AgreeValue { source: string; twh: number; ratio?: number; band?: string;
  national?: boolean; publisher?: string; url?: string }
/** The value a country's others are measured against; `source` names it in `values`. */
export interface AgreeRef { source: string; kind: "national-adapter" | "national-figure" | "eurostat" | "ember";
  name: string; publisher?: string; url?: string; why: string }
export interface Agreement { checked: string; year: number;
  countries: Record<string, { reference: AgreeRef; values: AgreeValue[] }>;
  steps: { source: string; stated_minutes: number; observed_minutes: number; agrees: boolean }[];
  failures: { source: string; error?: string }[] }
export interface Checks { links?: { checked: string; summary: Record<string, number>;
  entries: Record<string, LinkRow> }; agreement?: Agreement;
  snippets?: Record<string, SnippetRun> }
export interface SnippetRun { result: "ok" | "failed" | "skipped"; checked: string; last_ok?: string;
  seconds?: number; summary?: string; error?: string; reason?: string }
/** `mw`: capacity behind the point where known. `iso`: set only when the entry spans countries. */
export interface Farm { name: string; entry: string; n: number; lat: number; lon: number;
  osm?: string; located_by: string; turbine?: boolean; mw?: number; iso?: string }
export interface Farms { licence: string; farms: Farm[] }
