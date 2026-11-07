<script lang="ts">
  import { hasLive } from "../live";
  import { REPO, store, type Indexed } from "../store.svelte";
  import { BAND_TEXT, REF_NAME, STAMP, TEXT, VALUE, coverageText, twh, zoneText } from "../text";
  import CopyButton from "./CopyButton.svelte";
  import Ext from "./Ext.svelte";
  import Icon from "./Icon.svelte";
  import LevelDot from "./LevelDot.svelte";
  import LiveChart from "./LiveChart.svelte";
  import Snippet from "./Snippet.svelte";
  import Verdict from "./Verdict.svelte";

  let { s }: { s: Indexed } = $props();
  let traps = $derived(s.traps ?? []);
  let links = $derived(store.checks.links?.entries[s.id]);
  let agr = $derived(store.checks.agreement);
  let comps = $derived.by(() => {
    if (!agr) return [];
    const out: { iso: string; twh: number; ratio?: number; band?: string; ref: string; refTwh: number }[] = [];
    for (const [iso, c] of Object.entries(agr.countries)) {
      const ref = c.values.find((v) => v.source === c.reference);
      for (const v of c.values) if (v.source === s.id && v.source !== c.reference && ref)
        out.push({ iso, twh: v.twh, ratio: v.ratio, band: v.band, ref: c.reference, refTwh: ref.twh });
    }
    return out;
  });
  let asRef = $derived(agr ? Object.values(agr.countries).filter((c) => c.reference === s.id).length : 0);
  let step = $derived(agr?.steps.find((x) => x.source === s.id));
  let entryLink = $derived(`${location.origin}${location.pathname}?source=${encodeURIComponent(s.id)}`);
  const yesNo = (v?: boolean) => (v == null ? "" : v ? "Yes" : "No");
  let notCross = $derived(s.access.key_required ? "it needs a key" : s.access.method === "api" ? "no reader is written for it yet" : "it is not read by machine yet");
</script>

<article class="detail">
  <header>
    <h2>{s.name}</h2>
    <p class="pub">{s.publisher}{s.publisher_role ? `, ${TEXT.role[s.publisher_role]?.toLowerCase() ?? s.publisher_role}` : ""}</p>
    <p class="id"><code>{s.id}</code>
      {#if s.status !== "active"}<span class="tag">{TEXT.status[s.status]}</span>{/if}
      {#if s.reviewed === false}<span class="tag dashed">Unreviewed</span>{/if}</p>
  </header>

  <dl class="facts">
    <div><dt>Finest level</dt><dd class="lvl"><LevelDot tier={s._tier} size={10} />{TEXT.level[s.level]}</dd></div>
    <div><dt>Time step</dt><dd>{TEXT.step[s.resolution]}</dd></div>
    <div><dt>Re-hosting</dt><dd><Verdict value={s.licence.redistribution} /></dd></div>
    <div><dt>Coverage</dt><dd class="num">{coverageText(s.coverage)}</dd></div>
    <div><dt>Access</dt><dd>{TEXT.method[s.access.method]}{s.access.key_required ? ", key needed" : ", no key"}</dd></div>
    <div><dt>Area</dt><dd>{s.countries.length > 4 ? `${s.countries.length} countries` : s.countries.map(store.placeName).join(", ")}</dd></div>
  </dl>

  <section>
    <h3>Known traps <span class="count num">{traps.length}</span></h3>
    {#if traps.length}
      <ol class="traps">
        {#each traps as t, i (i)}
          <li>
            <p class="ts">{t.summary}</p>
            {#if t.detail}<p class="td">{t.detail}</p>{/if}
            <p class="te">Evidence: <Ext href={t.evidence} />{#if t.found}<span class="sub"> · found {t.found}</span>{/if}</p>
          </li>
        {/each}
      </ol>
    {:else}
      <p class="muted">None recorded yet. That is not the same as none existing.</p>
    {/if}
  </section>

  <div class="actions">
    <a class="primary" href={s.access.url} target="_blank" rel="noopener">Open the data<Icon name="out" size={14} /></a>
    <CopyButton text={s.access.url} what="access URL" label="Copy URL" />
    <CopyButton text={entryLink} what="link to this entry" label="Copy link" />
  </div>

  {#if s.reviewed === false}
    <p class="note">Compiled by an automated research pass from the publisher's own pages. A person has not checked it yet, so treat the details as leads.</p>
  {/if}

  {#if hasLive(s.id)}
    <section><LiveChart id={s.id} /></section>
  {/if}

  {#if s.conventions}
    {@const c = s.conventions}
    <section>
      <h3>Reading the data</h3>
      <dl class="kv">
        <div><dt>Time zone</dt><dd class:unk={c.timezone === "unknown"}>{zoneText(c.timezone)}</dd></div>
        <div><dt>Time stamp</dt><dd class:unk={c.timestamp === "unknown"}>The stamp {STAMP[c.timestamp] ?? c.timestamp}</dd></div>
        <div><dt>Values</dt><dd class:unk={c.value === "unknown" && c.unit === "unknown"}>{c.unit === "unknown" ? "Unit not stated" : c.unit}, {VALUE[c.value] ?? c.value}</dd></div>
        <div><dt>Stated in</dt><dd><Ext href={c.evidence} /></dd></div>
      </dl>
      {#if c.note}<p class="conv-note">{c.note}</p>{/if}
    </section>
  {/if}

  {#if s.snippet}<Snippet id={s.id} />{/if}

  <section>
    <h3>Access</h3>
    <dl class="kv">
      <div><dt>Where</dt><dd><Ext href={s.access.url} /></dd></div>
      {#if s.access.docs}<div><dt>Documentation</dt><dd><Ext href={s.access.docs} /></dd></div>{/if}
      <div><dt>Method</dt><dd>{TEXT.method[s.access.method]}</dd></div>
      <div><dt>Key required</dt><dd>{yesNo(s.access.key_required)}</dd></div>
      {#if s.access.registration != null}<div><dt>Registration</dt><dd>{yesNo(s.access.registration)}</dd></div>{/if}
      {#if s.access.formats?.length}<div><dt>Formats</dt><dd>{s.access.formats.join(", ").toUpperCase()}</dd></div>{/if}
      {#if s.access.languages?.length}<div><dt>Languages</dt><dd>{s.access.languages.join(", ")}</dd></div>{/if}
      {#if s.tools?.length}<div><dt>Readers</dt><dd>{#each s.tools as t, i (t.url)}{i ? ", " : ""}<Ext href={t.url} label={t.name} />{t.language ? ` (${t.language})` : ""}{/each}</dd></div>{/if}
    </dl>
  </section>

  <section>
    <h3>Licence</h3>
    <dl class="kv">
      <div><dt>Re-hosting</dt><dd><Verdict value={s.licence.redistribution} /></dd></div>
      <div><dt>Terms</dt><dd>{#if s.licence.url}<Ext href={s.licence.url} label={s.licence.name} />{:else}{s.licence.name}{/if}{#if s.licence.spdx}<span class="sub"> · {s.licence.spdx}</span>{/if}</dd></div>
      <div><dt>Read on the publisher's page</dt><dd>{s.licence.verified ? "Yes" : "Not yet"}</dd></div>
      {#if s.licence.attribution}<div><dt>Credit line</dt><dd class="cred"><q>{s.licence.attribution}</q><CopyButton text={s.licence.attribution} what="credit line" /></dd></div>{/if}
      {#if s.licence.note}<div><dt>Note</dt><dd>{s.licence.note}</dd></div>{/if}
    </dl>
  </section>

  <section>
    <h3>The data</h3>
    <dl class="kv">
      <div><dt>Measure</dt><dd>{TEXT.measure[s.measure]}</dd></div>
      <div><dt>Level</dt><dd>{TEXT.levelLong[s.level]}</dd></div>
      <div><dt>Technology</dt><dd>{TEXT.technology[s.technology]}</dd></div>
      <div><dt>Time step</dt><dd>{TEXT.step[s.resolution]}</dd></div>
      {#if s.coverage.update}<div><dt>Updates</dt><dd>{s.coverage.update}</dd></div>{/if}
      {#if s.area}<div><dt>Area</dt><dd>{s.area}</dd></div>{/if}
      {#if s.countries.length > 4}<div><dt>Countries</dt><dd class="codes">{s.countries.join(" ")}</dd></div>{/if}
      <div><dt>Capacity</dt><dd>{TEXT.presence[s.capacity]}</dd></div>
      <div><dt>Coordinates</dt><dd>{TEXT.presence[s.coordinates]}</dd></div>
      <div><dt>Curtailment</dt><dd>{TEXT.curtailment[s.curtailment ?? "unknown"]}</dd></div>
    </dl>
  </section>

  <section>
    <h3>Checks</h3>
    <dl class="kv">
      <div><dt>Reviewed</dt><dd>{s.reviewed === false ? "Not yet by a person" : `By a person, ${s.last_checked}`}</dd></div>
      <div><dt>Links</dt><dd>
        {#if links}
          {links.ok} of {links.total} answer<span class="sub"> · {store.checks.links?.checked}</span>
          {#each links.broken as b (b.url)}<span class="bad">Broken: <Ext href={b.url} /> ({b.role})</span>{/each}
          {#each links.recheck as b (b.url)}<span class="bad">Now loads, so the trap may be fixed: <Ext href={b.url} /></span>{/each}
          {#if links.unchecked.length}<span class="sub block">{links.unchecked.length} refused or timed out on an automated check, so they were not judged.</span>{/if}
        {:else}Not checked yet{/if}
      </dd></div>
      {#if agr}
        <div><dt>Annual total, {agr.year}</dt><dd>
          {#if comps.length === 1}
            {@const r = comps[0]}
            {twh(r.twh)} TWh against {REF_NAME[r.ref]}'s {twh(r.refTwh)} TWh{#if r.ratio != null}: ratio <span class="num">{r.ratio.toFixed(2)}</span>, {BAND_TEXT[r.band ?? "small"].toLowerCase()}{/if}.
          {:else if comps.length > 1}
            Compared for {comps.length} countries: {comps.filter((r) => r.band === "agrees").length} within 15%.
            {@const off = comps.filter((r) => r.band === "outside" || r.band === "noted")}
            {#if off.length}<span class="block">Further out: {#each off as r, i (r.iso)}{i ? ", " : ""}<button type="button" class="lnk" onclick={() => store.go({ country: r.iso, source: "" })}>{store.placeName(r.iso)}</button> <span class="num">{r.ratio?.toFixed(2)}</span>{/each}</span>{/if}
          {:else if asRef}
            The reference for {asRef} countries in the cross-check.
          {:else if agr.failures.some((f) => f.source === s.id)}
            The reader failed on the last run.
          {:else}
            <span class="sub">Not cross-checked: {notCross}.</span>
          {/if}
        </dd></div>
      {/if}
      {#if step}<div><dt>Time step found</dt><dd>{#if step.agrees}{step.observed_minutes} minutes in the {agr?.year} data, as stated{:else}<span class="bad">States {step.stated_minutes} minutes; the data show {step.observed_minutes}</span>{/if}</dd></div>{/if}
    </dl>
  </section>

  {#if s.notes}
    <section><h3>Notes</h3><p class="prose">{s.notes}</p></section>
  {/if}

  <footer>
    <p class="sub">Last checked {s.last_checked}{s.checked_by ? ` · ${s.checked_by}` : ""}</p>
    <a href="{REPO}/blob/main/sources/{s.id}.yaml" target="_blank" rel="noopener">Correct this entry on GitHub</a>
  </footer>
</article>

<style>
  .detail { display: grid; gap: 20px; }
  header { display: grid; gap: 4px; }
  h2 { font-size: 19px; line-height: 1.3; }
  .pub { color: var(--ink-2); }
  .id { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
  .id code { font-size: 12px; color: var(--ink-3); }
  .lvl { display: flex; align-items: center; gap: 6px; }
  .facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; margin: 0;
    background: var(--line); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
  .facts div { background: var(--surface); padding: 8px 10px; display: grid; gap: 1px; }
  .facts dt { font-size: 11.5px; color: var(--ink-3); }
  .facts dd { margin: 0; font-size: 13.5px; font-weight: 500; }
  .actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .primary { display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 12px; border-radius: var(--radius-sm);
    background: var(--accent); color: var(--surface); font-weight: 600; font-size: 13.5px; text-decoration: none; }
  .primary:hover { background: var(--accent-ink); }
  .note { padding: 10px 12px; border-radius: var(--radius); background: var(--surface-2); border: 1px dashed var(--line-strong);
    font-size: 13px; color: var(--ink-2); }
  section { display: grid; gap: 8px; }
  h3 { font-size: 14px; display: flex; align-items: center; gap: 8px; }
  .count { display: inline-grid; place-items: center; min-width: 20px; height: 20px; padding: 0 6px; border-radius: 10px;
    background: var(--surface-3); font-size: 12px; }
  .traps { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; counter-reset: t; }
  .traps li { position: relative; padding: 10px 12px 10px 38px; border-radius: var(--radius);
    background: var(--surface); border: 1px solid var(--line-strong); counter-increment: t; }
  .traps li::before { content: counter(t); position: absolute; left: 12px; top: 10px; width: 18px; height: 18px; display: grid; place-items: center;
    border-radius: 50%; background: var(--ink); color: var(--surface); font-size: 11px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .ts { font-weight: 600; font-size: 13.5px; line-height: 1.4; }
  .td { margin-top: 3px; font-size: 13px; color: var(--ink-2); }
  .te { margin-top: 5px; font-size: 12.5px; color: var(--ink-2); }
  .kv { margin: 0; display: grid; border-top: 1px solid var(--line); }
  .kv div { display: grid; grid-template-columns: 9.5rem minmax(0, 1fr); gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--line); }
  .kv dt { font-size: 12.5px; color: var(--ink-3); }
  .kv dd { margin: 0; font-size: 13.5px; overflow-wrap: anywhere; }
  .cred { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  q { font-style: italic; }
  .codes { font-family: var(--mono); font-size: 12px; line-height: 1.6; }
  .sub { color: var(--ink-3); }
  .block { display: block; margin-top: 2px; }
  .bad { display: block; color: var(--bad); }
  .muted { color: var(--ink-3); font-size: 13px; }
  .prose { font-size: 13.5px; color: var(--ink-2); max-width: 68ch; }
  .lnk { border: 0; background: none; padding: 0; color: var(--accent-ink); text-decoration: underline; text-underline-offset: 0.18em; }
  .tag { display: inline-flex; align-items: center; padding: 0 6px; height: 18px; border-radius: 9px; background: var(--surface-3); font-size: 11px; font-weight: 500; }
  .tag.dashed { background: none; border: 1px dashed var(--line-strong); }
  footer { display: grid; gap: 4px; padding-top: 4px; font-size: 12.5px; }
  @media (max-width: 420px) { .kv div { grid-template-columns: 1fr; gap: 2px; } }
  .unk { color: var(--ink-3); font-style: italic; }
  .conv-note { font-size: 12.5px; color: var(--ink-2); margin: 6px 0 0; }
</style>
