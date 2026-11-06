"use strict";

// Where the repository will live once published. Used for "edit this entry" links.
const REPO = "https://github.com/ellyess/wind-generation-sources";

const CONTINENTS = [
  ["Europe", "AL AT BA BE BG BY CH CY CZ DE DK EE ES FI FR GB GE GR HR HU IE IS IT LT LU LV MD ME MK MT NL NO PL PT RO RS RU SE SI SK TR UA XK"],
  ["Americas", "AR BO BR CA CL CO CR EC GT HN MX NI PA PE PY SV US UY VE"],
  ["Asia", "CN ID IN JP KR KZ MY PH PK SA SG TH TW VN"],
  ["Oceania", "AU NZ"],
  ["Africa", "EG KE MA NG ZA"],
].map(([name, codes]) => [name, new Set(codes.split(" "))]);

const LEVELS = ["turbine", "farm", "connection-point", "complex", "company", "zone", "country"];
const STEPS = ["1min", "5min", "10min", "15min", "30min", "hourly", "daily", "monthly", "annual"];

const TEXT = {
  level: {
    turbine: "Turbine", farm: "Farm", "connection-point": "Connection point", complex: "Complex",
    company: "Company", zone: "Zone", country: "Country",
  },
  levelLong: {
    zone: "Zone (a market, balancing or reporting area)",
    complex: "Complex (several farms reported together)",
    "connection-point": "Connection point (output where it meets the grid)",
  },
  step: {
    "1min": "1 min", "5min": "5 min", "10min": "10 min", "15min": "15 min", "30min": "30 min",
    hourly: "Hourly", daily: "Daily", monthly: "Monthly", annual: "Annual",
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
    tso: "Transmission operator", "market-operator": "Market operator", "owner-operator": "Owner and operator",
    utility: "Utility", research: "Research body", "statistics-office": "Statistics office",
    government: "Government", aggregator: "Aggregator", "iso-rto": "Grid and market operator",
    regulator: "Regulator",
  },
};

const $ = (sel, root = document) => root.querySelector(sel);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");

function el(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return node;
}

function icon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("class", "ic");
  const use = document.createElementNS(ns, "use");
  use.setAttribute("href", `#i-${name}`);
  svg.append(use);
  return svg;
}

const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const continentOf = (code) => (CONTINENTS.find(([, set]) => set.has(code)) || ["Elsewhere"])[0];

function shortLink(url) {
  try {
    const u = new URL(url);
    const pyvwf = u.pathname.match(/^\/ellyess\/PyVWF\/blob\/[^/]+\/[^/]+\/(.+)$/);
    if (u.host === "github.com" && pyvwf) return `PyVWF audit: ${pyvwf[1]}`;
    let path = decodeURIComponent(u.pathname).replace(/\/$/, "");
    if (path.length > 36) path = `${path.slice(0, 34)}…`;
    return u.host.replace(/^www\./, "") + path;
  } catch {
    return url;
  }
}

function coverageText(cov) {
  const start = String(cov.start);
  return cov.end ? `${start}–${cov.end}` : `${start} on`;
}

function areaText(src) {
  const n = src.countries.length;
  return n <= 3 ? src.countries.join(" ") : `${n} countries`;
}

/* ---------- state ---------- */

const state = { place: "", level: "", step: "", reuse: "", status: "", q: "" };
let SOURCES = [];
const open = new Set();

function readURL() {
  const p = new URLSearchParams(location.search);
  for (const k of Object.keys(state)) state[k] = p.get(k) || "";
  const id = decodeURIComponent(location.hash.slice(1));
  if (id && SOURCES.some((s) => s.id === id)) open.add(id);
}

function writeURL(lastOpened) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(state)) if (v) p.set(k, v);
  const qs = p.toString();
  const hash = lastOpened ? `#${encodeURIComponent(lastOpened)}` : "";
  history.replaceState(null, "", `${location.pathname}${qs ? `?${qs}` : ""}${hash}`);
}

function matchesPlace(src, place) {
  if (!place) return true;
  if (place.startsWith("@")) {
    const name = place.slice(1);
    return src.countries.some((c) => continentOf(c) === name);
  }
  return src.countries.includes(place);
}

function matches(src, ignorePlace = false) {
  if (!ignorePlace && !matchesPlace(src, state.place)) return false;
  if (state.level && src.level !== state.level) return false;
  if (state.step && STEPS.indexOf(src.resolution) > STEPS.indexOf(state.step)) return false;
  if (state.status && src.status !== state.status) return false;
  if (state.reuse) {
    const r = src.licence.redistribution;
    if (state.reuse === "open" ? !(r === "allowed" || r === "allowed-with-attribution") : r !== state.reuse) {
      return false;
    }
  }
  if (state.q) {
    const words = fold(state.q).split(/\s+/).filter(Boolean);
    if (!words.every((w) => src._hay.includes(w))) return false;
  }
  return true;
}

/* ---------- title block, index, params ---------- */

function fillTitleBlock(data) {
  const traps = SOURCES.reduce((n, s) => n + (s.traps || []).length, 0);
  const set = (f, v) => { $(`[data-field="${f}"]`).textContent = v; };
  set("generated", data.generated);
  set("count", data.count);
  set("countries", data.countries.length);
  set("traps", traps);
  document.querySelectorAll("[data-repo]").forEach((a) => { a.href = REPO + a.dataset.repo; });
}

function buildIndex(codes) {
  const host = $("[data-index]");
  const groups = new Map(CONTINENTS.map(([name]) => [name, []]));
  for (const code of codes) {
    const c = continentOf(code);
    if (!groups.has(c)) groups.set(c, []);
    groups.get(c).push(code);
  }
  for (const [name, list] of groups) {
    if (!list.length) continue;
    host.append(el("div", { class: "index-row" },
      el("button", { type: "button", class: "index-group", "data-place": `@${name}`, "aria-pressed": "false" },
        el("span", { class: "ix-name", text: name }), el("span", { class: "ix-n" })),
      el("ul", { class: "index-codes", role: "list" }, list.map((code) =>
        el("li", {}, el("button", {
          type: "button", class: "index-code", "data-place": code, "aria-pressed": "false",
        }, el("span", { class: "ix-code", text: code }), el("span", { class: "ix-n" })))))));
  }
  host.addEventListener("click", (e) => {
    const b = e.target.closest("[data-place]");
    if (!b) return;
    state.place = state.place === b.dataset.place ? "" : b.dataset.place;
    update();
  });
  $("[data-clear-place]").addEventListener("click", () => { state.place = ""; update(); });
}

function buildParams() {
  const form = $("[data-params]");
  const levelSel = form.elements.level;
  for (const lv of LEVELS) {
    const n = SOURCES.filter((s) => s.level === lv).length;
    if (n) levelSel.append(el("option", { value: lv, text: TEXT.level[lv] }));
  }
  for (const k of ["level", "step", "reuse", "status", "q"]) form.elements[k].value = state[k];
  form.addEventListener("input", (e) => {
    const name = e.target.name;
    if (!(name in state)) return;
    state[name] = e.target.value.trim();
    update();
  });
  form.addEventListener("submit", (e) => e.preventDefault());
}

function syncIndex() {
  const others = SOURCES.filter((s) => matches(s, true));
  document.querySelectorAll("[data-place]").forEach((b) => {
    const n = others.filter((s) => matchesPlace(s, b.dataset.place)).length;
    $(".ix-n", b).textContent = n;
    b.classList.toggle("is-zero", n === 0);
    b.setAttribute("aria-pressed", String(state.place === b.dataset.place));
    const label = b.dataset.place.startsWith("@") ? b.dataset.place.slice(1) : b.dataset.place;
    b.setAttribute("aria-label", `${label}, ${n} source${n === 1 ? "" : "s"}`);
  });
  $("[data-clear-place]").hidden = !state.place;
}

/* ---------- rows ---------- */

const rowTpl = $("#row-tpl");

function makeRow(src) {
  const tr = rowTpl.content.firstElementChild.cloneNode(true);
  tr.dataset.id = src.id;
  tr.classList.add(`st-${src.status}`);
  $(".pn", tr).textContent = src.id;
  $(".flag", tr).textContent = src.status === "active" ? "" : TEXT.status[src.status];
  const btn = $(".open", tr);
  btn.setAttribute("aria-controls", `sheet-${src.id}`);
  $(".nm", tr).textContent = src.name;
  $(".pub", tr).textContent = src.publisher;
  const area = $(".area", tr);
  area.textContent = areaText(src);
  if (src.countries.length > 3) area.title = src.countries.join(" ");
  $(".level", tr).textContent = TEXT.level[src.level];
  $(".step", tr).textContent = TEXT.step[src.resolution];
  $(".cov", tr).textContent = coverageText(src.coverage);
  const r = src.licence.redistribution;
  $(".reuse", tr).append(el("span", { class: `verdict v-${r}` }, el("i", { "aria-hidden": "true" }), TEXT.reuse[r]));
  const n = (src.traps || []).length;
  const t = $(".traps", tr);
  t.textContent = n;
  if (!n) t.classList.add("is-none");
  return tr;
}

function field(label, ...value) {
  const kids = value.flat().filter((v) => v != null && v !== "");
  if (!kids.length) return null;
  return el("div", { class: "f" }, el("dt", { text: label }), el("dd", {}, kids));
}

function copyButton(text, what) {
  return el("button", { type: "button", class: "copy", "data-copy": text, "aria-label": `Copy ${what}` },
    icon("copy"), el("span", { text: "Copy" }));
}

function extLink(url, label) {
  return el("a", { href: url, rel: "noopener", class: "ext" }, label || shortLink(url), icon("out"));
}

function buildSheet(src) {
  const cov = src.coverage;
  const acc = src.access;
  const lic = src.licence;
  const yesNo = (v) => (v ? "Yes" : "No");

  const data = el("section", { class: "spec-sec" }, el("h3", { text: "Rated data" }), el("dl", {},
    field("Measure", TEXT.measure[src.measure]),
    field("Level", TEXT.levelLong[src.level] || TEXT.level[src.level]),
    field("Technology", TEXT.technology[src.technology]),
    field("Time step", TEXT.step[src.resolution]),
    field("Coverage", coverageText(cov)),
    field("Updates", cov.update),
    field("Countries", src.countries.length > 3 ? `${src.countries.length}: ${src.countries.join(" ")}` : src.countries.join(" ")),
    field("Area", src.area),
    field("Capacity", TEXT.presence[src.capacity]),
    field("Coordinates", TEXT.presence[src.coordinates]),
    field("Curtailment", TEXT.curtailment[src.curtailment || "unknown"]),
  ));

  const access = el("section", { class: "spec-sec" }, el("h3", { text: "Access" }), el("dl", {},
    field("Method", TEXT.method[acc.method]),
    field("Where", el("span", { class: "with-copy" }, extLink(acc.url), copyButton(acc.url, "access URL"))),
    field("Documentation", acc.docs && extLink(acc.docs)),
    field("Key required", yesNo(acc.key_required)),
    field("Registration", acc.registration == null ? null : yesNo(acc.registration)),
    field("Formats", (acc.formats || []).join(", ").toUpperCase()),
    field("Languages", (acc.languages || []).join(", ")),
    field("Publisher", src.publisher, src.publisher_role && el("span", { class: "sub", text: `\u00a0· ${TEXT.role[src.publisher_role] || src.publisher_role}` })),
  ));

  const r = lic.redistribution;
  const licence = el("section", { class: "spec-sec" }, el("h3", { text: "Licence" }), el("dl", {},
    field("Re-hosting", el("span", { class: `verdict v-${r}` }, el("i", { "aria-hidden": "true" }), TEXT.reuse[r])),
    field("Terms", lic.url ? extLink(lic.url, lic.name) : lic.name, lic.spdx && el("span", { class: "sub", text: `\u00a0· ${lic.spdx}` })),
    field("Read on publisher's page", lic.verified ? "Yes" : "Not yet"),
    field("Credit line", lic.attribution && el("span", { class: "with-copy" },
      el("span", { class: "quote", text: lic.attribution }), copyButton(lic.attribution, "credit line"))),
    field("Note", lic.note),
  ));

  const traps = src.traps || [];
  const trapSec = el("section", { class: "spec-sec spec-traps" },
    el("h3", {}, "Known traps ", el("span", { class: "count", text: traps.length })),
    traps.length
      ? el("ol", { class: "trap-list" }, traps.map((t, i) => el("li", { class: "trap" },
          el("span", { class: "tn", "aria-hidden": "true", text: i + 1 }),
          el("div", { class: "tb" },
            el("p", { class: "ts", text: t.summary }),
            t.detail && el("p", { class: "td", text: t.detail }),
            el("p", { class: "te" }, el("span", { class: "te-l", text: "Evidence" }), extLink(t.evidence),
              t.found && el("span", { class: "sub", text: `found ${t.found}` }))))))
      : el("p", { class: "none", text: "None recorded yet. That is not the same as none existing." }),
  );

  const tools = src.tools || [];
  const notes = el("section", { class: "spec-sec spec-notes" }, el("h3", { text: "Notes" }),
    src.notes && el("p", { class: "nt", text: src.notes }),
    tools.length && el("p", { class: "tools" }, el("span", { class: "te-l", text: "Readers" }),
      tools.map((t, i) => [i ? ", " : "", el("a", { href: t.url, rel: "noopener" }, t.name), t.language ? ` (${t.language})` : ""])),
    farmList(src.id),
    el("p", { class: "checked" },
      el("span", { class: "te-l", text: "Last checked" }), el("time", { datetime: src.last_checked, text: src.last_checked }),
      src.checked_by && el("span", { class: "sub", text: `\u00a0· ${src.checked_by}` })),
    el("p", { class: "actions" },
      el("a", { href: `${REPO}/blob/main/sources/${src.id}.yaml` }, "Correct this entry"),
      el("button", { type: "button", class: "copy linkcopy", "data-copy-link": src.id, "aria-label": "Copy a link to this entry" },
        icon("copy"), el("span", { text: "Copy link to entry" }))),
  );

  return el("tr", { class: "sheet-row", role: "row", id: `sheet-${src.id}` },
    el("td", { colspan: "8", role: "cell" }, el("div", { class: "unfold" }, el("div", { class: "unfold-in" },
      el("div", { class: "spec" }, trapSec, access, licence, data, notes)))));
}

function setOpen(tr, want, { scroll = false, instant = false } = {}) {
  const id = tr.dataset.id;
  const btn = $(".open", tr);
  let sheet = tr.nextElementSibling;
  if (!sheet || !sheet.classList.contains("sheet-row")) sheet = null;
  if (want) {
    if (!sheet) {
      sheet = buildSheet(SOURCES.find((s) => s.id === id));
      tr.after(sheet);
    }
    sheet.hidden = false;
    open.add(id);
    tr.classList.add("is-open");
    btn.setAttribute("aria-expanded", "true");
    if (instant || reduceMotion.matches) sheet.classList.add("is-open");
    else requestAnimationFrame(() => requestAnimationFrame(() => sheet.classList.add("is-open")));
    if (scroll) tr.scrollIntoView({ block: "start" });
  } else if (sheet) {
    open.delete(id);
    tr.classList.remove("is-open");
    btn.setAttribute("aria-expanded", "false");
    sheet.classList.remove("is-open");
    const done = () => { if (!open.has(id)) sheet.hidden = true; };
    if (reduceMotion.matches) done();
    else setTimeout(done, 220);
  }
}

function renderRows() {
  const body = $("[data-rows]");
  const shown = SOURCES.filter((s) => matches(s));
  body.replaceChildren();
  if (!shown.length) {
    body.append(el("tr", { class: "state-row", role: "row" }, el("td", { colspan: "8", role: "cell" }, el("div", { class: "state" },
      el("p", { text: "No source matches these settings." }),
      el("button", { type: "button", class: "reset", "data-reset": "" }, "Clear every filter")))));
  }
  for (const src of shown) {
    const tr = makeRow(src);
    body.append(tr);
    if (open.has(src.id)) setOpen(tr, true, { instant: true });
  }
  $("[data-count]").textContent = shown.length === SOURCES.length
    ? `${shown.length} sources`
    : `${shown.length} of ${SOURCES.length}`;
}

function update(lastOpened) {
  syncIndex();
  syncMap();
  renderRows();
  writeURL(lastOpened);
}

/* ---------- events ---------- */

const live = el("p", { class: "visually-hidden", "aria-live": "polite" });
document.body.append(live);

async function copyText(btn, text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    live.textContent = "Copy failed. Select the text and copy it by hand.";
    return;
  }
  const label = $("span", btn);
  const before = label.textContent;
  btn.classList.add("is-done");
  btn.replaceChild(icon("check"), $("svg", btn));
  label.textContent = "Copied";
  live.textContent = "Copied to the clipboard.";
  setTimeout(() => {
    btn.classList.remove("is-done");
    btn.replaceChild(icon("copy"), $("svg", btn));
    label.textContent = before;
  }, 1600);
}

function wireTable() {
  const body = $("[data-rows]");
  body.addEventListener("click", (e) => {
    const copy = e.target.closest("[data-copy]");
    if (copy) return copyText(copy, copy.dataset.copy);
    const link = e.target.closest("[data-copy-link]");
    if (link) {
      const url = new URL(location.href);
      url.search = "";
      url.hash = link.dataset.copyLink;
      return copyText(link, url.href);
    }
    if (e.target.closest("[data-reset]")) {
      for (const k of Object.keys(state)) state[k] = "";
      const form = $("[data-params]");
      for (const k of ["level", "step", "reuse", "status", "q"]) form.elements[k].value = "";
      return update();
    }
    const tr = e.target.closest("tr.row");
    if (!tr) return;
    if (e.target.closest("a") || (!e.target.closest(".open") && String(getSelection()).length)) return;
    const want = !open.has(tr.dataset.id);
    setOpen(tr, want);
    writeURL(want ? tr.dataset.id : "");
  });
}

/* ---------- start ---------- */

async function start() {
  let data;
  try {
    const res = await fetch("catalogue.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    data = await res.json();
  } catch (err) {
    $("[data-rows]").replaceChildren(el("tr", { class: "state-row", role: "row" }, el("td", { colspan: "8", role: "cell" },
      el("p", { class: "state is-error" },
        `The catalogue file could not be loaded (${err.message}). Reload the page, or download `,
        el("a", { href: "catalogue.csv" }, "catalogue.csv"), " directly."))));
    return;
  }
  SOURCES = [...data.sources].sort((a, b) => a.id.localeCompare(b.id)).map((s) => ({
    ...s,
    _hay: fold([s.id, s.name, s.publisher, s.countries.join(" "), s.area, s.notes, s.licence.name,
      ...(s.traps || []).map((t) => `${t.summary} ${t.detail || ""}`)].filter(Boolean).join(" ")),
  }));
  readURL();
  fillTitleBlock(data);
  buildIndex(data.countries);
  initMap(data.countries);
  buildParams();
  wireTable();
  const params = $("[data-params]");
  new ResizeObserver(() => {
    const sticky = getComputedStyle(params).position === "sticky";
    document.documentElement.style.setProperty("--params-h", sticky ? `${params.offsetHeight}px` : "0px");
  }).observe(params);
  update([...open].pop());
  addEventListener("hashchange", () => {
    const id = decodeURIComponent(location.hash.slice(1));
    const tr = id && $(`tr.row[data-id="${CSS.escape(id)}"]`);
    if (tr) setOpen(tr, true, { scroll: true });
  });
  const first = [...open].pop();
  if (first) {
    const tr = $(`tr.row[data-id="${CSS.escape(first)}"]`);
    if (tr) document.fonts.ready.then(() => requestAnimationFrame(() => tr.scrollIntoView({ block: "start" })));
  }
}

start();
