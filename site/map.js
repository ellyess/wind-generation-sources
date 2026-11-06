"use strict";

// The map sheet: View 1 (world, Equal Earth) and Detail A (Europe, Lambert azimuthal equal-area).
// Paths arrive projected from the build (map.json). Countries are shaded by the finest observed
// level among the sources that pass every filter except place; picking one sets the same place
// filter as its cell in the code index. Uses state, matches, update and the helpers in app.js.

const SVG_NS = "http://www.w3.org/2000/svg";

// Four tints, darkest for the finest level. Tier 0 is "no source under these filters".
const TIER = { turbine: 1, farm: 2, "connection-point": 2, complex: 2, company: 3, zone: 3, country: 4 };
const LOCATED_BY = { osm: "OpenStreetMap", repd: "Renewable Energy Planning Database" };
const MARK_PX = 2.25; // farm mark radius on screen, in CSS pixels

const map = {
  ready: false,
  names: new Map(), // iso -> name
  paths: new Map(), // iso -> [path, ...] across both views
  catalogued: new Set(),
  tiers: new Map(), // iso -> tier under current filters
  finest: new Map(), // iso -> [source, ...] at the finest tier
  counts: new Map(), // iso -> matching source count
  farms: [],
  farmLicence: "",
  hover: null, // {kind: "country", iso} | {kind: "farm", farm}
  farm: null, // selected farm
};

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) node.setAttribute(k, v);
  return node;
}

function drawView(svg, view, extra) {
  svg.setAttribute("viewBox", view.viewBox);
  const lines = svgEl("g", { class: "m-lines" });
  if (view.graticule) lines.append(svgEl("path", { class: "m-grat", d: view.graticule }));
  const land = svgEl("g", { class: "m-land" });
  for (const c of view.countries) {
    const p = svgEl("path", { d: c.d, class: "m-c", "data-iso": c.iso || null });
    land.append(p);
    if (!c.iso) continue;
    if (!map.names.has(c.iso)) map.names.set(c.iso, c.name);
    if (!map.paths.has(c.iso)) map.paths.set(c.iso, []);
    map.paths.get(c.iso).push(p);
    if (map.catalogued.has(c.iso)) p.classList.add("is-cat");
  }
  const top = svgEl("g", { class: "m-top" });
  if (view.frame) top.append(svgEl("path", { class: "m-frame", d: view.frame }));
  if (extra) top.append(extra);
  const sel = svgEl("g", { class: "m-sel" });
  const hov = svgEl("path", { class: "m-hov" });
  const marks = svgEl("g", { class: "m-farms" });
  svg.replaceChildren(lines, land, top, sel, hov, marks);
}

function drawFarms(svg, key) {
  const g = $(".m-farms", svg);
  for (const farm of map.farms) {
    const at = farm[key];
    // Farms inside Detail A are drawn there only; View 1 keeps the rest of the world.
    if (!at || (key === "w" && farm.e)) continue;
    const mark = svgEl("g", { class: "m-farm" });
    mark._farm = farm;
    mark.append(svgEl("circle", { class: "m-hit", cx: at[0], cy: at[1] }),
      svgEl("circle", { class: "m-dot", cx: at[0], cy: at[1] }));
    g.append(mark);
    (farm._marks ||= []).push(mark);
  }
}

// Mark radii are set in screen pixels, so convert through each view's current scale.
function sizeMarks(svg) {
  const vb = svg.viewBox.baseVal;
  if (!vb || !svg.clientWidth) return;
  const k = vb.width / svg.clientWidth;
  svg.querySelectorAll(".m-dot").forEach((c) => c.setAttribute("r", (MARK_PX * k).toFixed(2)));
  svg.querySelectorAll(".m-hit").forEach((c) => c.setAttribute("r", (MARK_PX * 1.7 * k).toFixed(2)));
}

/* ---------- state from filters ---------- */

function computeTiers() {
  const others = SOURCES.filter((s) => matches(s, true));
  map.tiers.clear();
  map.finest.clear();
  map.counts.clear();
  for (const s of others) {
    const t = TIER[s.level];
    for (const iso of s.countries) {
      map.counts.set(iso, (map.counts.get(iso) || 0) + 1);
      const cur = map.tiers.get(iso);
      if (cur == null || t < cur) {
        map.tiers.set(iso, t);
        map.finest.set(iso, [s]);
      } else if (t === cur) {
        map.finest.get(iso).push(s);
      }
    }
  }
  return new Set(others.map((s) => s.id));
}

function placeCodes() {
  if (!state.place) return [];
  if (state.place.startsWith("@")) {
    const name = state.place.slice(1);
    return [...map.catalogued].filter((c) => continentOf(c) === name);
  }
  return [state.place];
}

function syncMap() {
  if (!map.ready) return;
  const live = computeTiers();
  for (const [iso, paths] of map.paths) {
    const t = map.tiers.get(iso) || 0;
    for (const p of paths) p.setAttribute("data-tier", String(t));
  }
  for (const farm of map.farms) {
    farm._shown = live.has(farm.entry);
    for (const m of farm._marks || []) {
      m.classList.toggle("is-hidden", !farm._shown);
      m.classList.toggle("is-picked", farm === map.farm);
    }
  }
  if (map.farm && !map.farm._shown) map.farm = null;

  // Selection outline, drawn above the land so shared borders are not hidden by neighbours.
  const picked = new Set(placeCodes());
  document.querySelectorAll("[data-map-view]").forEach((svg) => {
    const g = $(".m-sel", svg);
    g.classList.toggle("is-group", state.place.startsWith("@"));
    g.replaceChildren();
    $(".m-land", svg).querySelectorAll("[data-iso]").forEach((p) => {
      if (picked.has(p.dataset.iso)) g.append(svgEl("path", { d: p.getAttribute("d") }));
    });
  });

  // Key counts: catalogued countries per tier.
  const per = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 };
  for (const iso of map.catalogued) per[map.tiers.get(iso) || 0] += 1;
  document.querySelectorAll("[data-tier-n]").forEach((n) => { n.textContent = per[n.dataset.tierN]; });
  $("[data-farm-n]").textContent = map.farms.filter((f) => f._shown).length;

  $("#map-summary").textContent = `Map of the ${map.catalogued.size} catalogued countries, shaded by the`
    + ` finest observed level under the current filters: ${per[1]} turbine, ${per[2]} farm, complex or`
    + ` connection point, ${per[3]} zone or company, ${per[4]} national total only, and ${per[0]} with`
    + ` nothing that matches. ${map.farms.filter((f) => f._shown).length} farms whose units publish`
    + ` their own output are marked; each entry's spec sheet in the table lists them. Use the country`
    + ` index below to filter by keyboard.`;
  renderReadout();
}

/* ---------- readout ---------- */

function roField(label, ...value) {
  return el("div", {}, el("dt", { text: label }), el("dd", {}, ...value));
}

function countryReadout(iso, picked) {
  const name = map.names.get(iso) || iso;
  const head = el("p", { class: "ro-title" }, el("span", { class: "ro-code", text: iso }), name);
  if (!map.catalogued.has(iso)) {
    return [head, el("p", { class: "ro-text" }, "No source catalogued yet. ",
      el("a", { href: `${REPO}/blob/main/CONTRIBUTING.md` }, "Add one"), ".")];
  }
  const n = map.counts.get(iso) || 0;
  const t = map.tiers.get(iso) || 0;
  const fin = map.finest.get(iso) || [];
  const out = [head, el("dl", { class: "ro-fields" },
    roField("Finest level", t ? TEXT.level[fin[0].level] : "None under these filters"),
    t ? roField("From", fin.slice(0, 2).map((s, i) => [i ? "; " : "", s.name]),
      fin.length > 2 ? `; and ${fin.length - 2} more` : "") : null,
    roField("Sources", `${n} match${n === 1 ? "es" : ""} the filters`))];
  if (picked) {
    out.push(el("p", { class: "ro-act" },
      n ? el("a", { href: "#sources" }, `Show ${n === 1 ? "it" : `the ${n}`} below`) : null,
      el("button", { type: "button", class: "ro-clear", "data-map-clear": "" }, "Clear")));
  } else {
    out.push(el("p", { class: "ro-text" }, state.place === iso ? "Selected." : "Click to filter the table."));
  }
  return out;
}

function farmReadout(farm, picked) {
  const src = SOURCES.find((s) => s.id === farm.entry);
  const units = farm.units.length;
  const out = [
    el("p", { class: "ro-title" }, farm.name),
    el("dl", { class: "ro-fields" },
      roField(units === 1 ? "Unit" : `${units} units`, el("span", { class: "ro-mono", text: farm.units.join(" ") })),
      roField("Output in", src ? src.name : farm.entry),
      roField("Located by", LOCATED_BY[farm.located_by] || farm.located_by)),
  ];
  if (picked) {
    out.push(el("p", { class: "ro-act" },
      el("button", { type: "button", class: "ro-link", "data-open-entry": farm.entry }, "Open the entry"),
      farm.osm ? el("a", { href: farm.osm, rel: "noopener" }, "OpenStreetMap") : null));
  } else {
    out.push(el("p", { class: "ro-text", text: farm.osm
      ? "Click for the entry and the OpenStreetMap link." : "Click for the entry." }));
  }
  return out;
}

function renderReadout() {
  const host = $("[data-readout]");
  let body;
  const h = map.hover;
  if (h && h.kind === "farm") body = farmReadout(h.farm, h.farm === map.farm);
  else if (h && h.kind === "country") body = countryReadout(h.iso, h.iso === state.place);
  else if (map.farm) body = farmReadout(map.farm, true);
  else if (state.place && !state.place.startsWith("@")) body = countryReadout(state.place, true);
  else if (state.place) {
    const codes = placeCodes();
    body = [el("p", { class: "ro-title" }, state.place.slice(1)),
      el("p", { class: "ro-text" }, `${codes.length} catalogued countries selected from the index.`),
      el("p", { class: "ro-act" }, el("button", { type: "button", class: "ro-clear", "data-map-clear": "" }, "Clear"))];
  } else {
    body = [el("p", { class: "ro-title is-idle", text: "Nothing selected" }),
      el("p", { class: "ro-text", text: "Point at a country to read its finest level. Click it to filter the table; click again to clear." })];
  }
  host.replaceChildren(...body.flat());
}

/* ---------- farm list in a spec sheet (the keyboard route to the marks) ---------- */

function farmList(id) {
  const farms = map.farms.filter((f) => f.entry === id);
  if (!farms.length) return null;
  const units = farms.reduce((n, f) => n + f.units.length, 0);
  return el("details", { class: "farmlist" },
    el("summary", {}, `${farms.length} farms located for ${units} units`),
    el("p", { class: "fl-note", text: map.farmLicence }),
    el("ul", { role: "list" }, farms.map((f) => el("li", {},
      el("span", { class: "fl-name", text: f.name }),
      el("span", { class: "fl-units", text: f.units.join(" ") }),
      f.osm ? el("a", { href: f.osm, rel: "noopener" }, "OpenStreetMap")
        : el("span", { class: "fl-src", text: "Located from REPD" })))));
}

/* ---------- events ---------- */

function targetOf(e) {
  const farm = e.target.closest(".m-farm");
  if (farm && !farm.classList.contains("is-hidden")) return { kind: "farm", farm: farm._farm };
  const c = e.target.closest("[data-iso]");
  if (c) return { kind: "country", iso: c.dataset.iso };
  return null;
}

function setHover(t) {
  const same = (a, b) => a === b || (a && b && a.kind === b.kind && a.iso === b.iso && a.farm === b.farm);
  if (same(map.hover, t)) return;
  map.hover = t;
  document.querySelectorAll("[data-map-view]").forEach((svg) => {
    const hov = $(".m-hov", svg);
    const p = t && t.kind === "country" && $(`.m-land [data-iso="${t.iso}"]`, svg);
    if (p) hov.setAttribute("d", p.getAttribute("d"));
    else hov.removeAttribute("d");
  });
  renderReadout();
}

function openEntry(id) {
  let tr = $(`tr.row[data-id="${CSS.escape(id)}"]`);
  if (!tr) {
    state.place = "";
    update();
    tr = $(`tr.row[data-id="${CSS.escape(id)}"]`);
  }
  if (!tr) return;
  setOpen(tr, true, { scroll: true });
  writeURL(id);
}

function wireMap() {
  const sheet = $("[data-map]");
  sheet.addEventListener("pointerover", (e) => {
    if (e.target.closest("[data-map-view]")) setHover(targetOf(e));
  });
  sheet.addEventListener("pointerleave", () => setHover(null));
  document.querySelectorAll("[data-map-view]").forEach((svg) => {
    svg.addEventListener("pointerleave", () => setHover(null));
    svg.addEventListener("click", (e) => {
      const t = targetOf(e);
      if (t && t.kind === "farm") {
        map.farm = map.farm === t.farm ? null : t.farm;
        return syncMap();
      }
      map.farm = null;
      if (t && map.catalogued.has(t.iso)) {
        state.place = state.place === t.iso ? "" : t.iso;
        return update();
      }
      syncMap();
    });
  });
  $("[data-readout]").addEventListener("click", (e) => {
    if (e.target.closest("[data-map-clear]")) {
      map.farm = null;
      state.place = "";
      return update();
    }
    const open = e.target.closest("[data-open-entry]");
    if (open) openEntry(open.dataset.openEntry);
  });
}

async function initMap(countries) {
  const host = $("[data-map]");
  map.catalogued = new Set(countries);
  let geo, farms;
  try {
    const get = async (f) => {
      const res = await fetch(f, { cache: "no-cache" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    };
    [geo, farms] = await Promise.all([get("map.json"), get("farms.json")]);
  } catch (err) {
    host.classList.add("is-error");
    $("[data-map-state]").textContent = `The map could not be loaded (${err.message}). The country index below lists the same countries.`;
    return;
  }
  map.farms = farms.farms;
  map.farmLicence = farms.licence;
  $("[data-farm-licence]").textContent = farms.licence;
  const world = $('[data-map-view="world"]');
  const europe = $('[data-map-view="europe"]');
  const detail = svgEl("path", { class: "m-detail", d: geo.detail.d });
  drawView(world, geo.world, detail);
  drawView(europe, geo.europe);
  drawFarms(world, "w");
  drawFarms(europe, "e");
  const [vw, vh] = geo.world.viewBox.split(" ").slice(2).map(Number);
  const tag = $("[data-detail-tag]");
  tag.style.left = `${(geo.detail.label[0] / vw) * 100}%`;
  tag.style.top = `${(geo.detail.label[1] / vh) * 100}%`;
  tag.hidden = false;
  host.classList.add("is-ready");
  $("[data-map-state]").remove();
  const ro = new ResizeObserver((entries) => entries.forEach((en) => sizeMarks(en.target)));
  ro.observe(world);
  ro.observe(europe);
  wireMap();
  // Sheets opened from a deep link were built before the farms arrived.
  document.querySelectorAll(".sheet-row").forEach((row) => {
    const notes = $(".spec-notes", row);
    const list = notes && !$(".farmlist", notes) && farmList(row.id.replace(/^sheet-/, ""));
    if (list) $(".checked", notes).before(list);
  });
  map.ready = true;
  syncMap();
}
