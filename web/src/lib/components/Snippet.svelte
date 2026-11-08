<script lang="ts">
  import { REPO, store } from "../store.svelte";
  import CopyButton from "./CopyButton.svelte";
  import Icon from "./Icon.svelte";

  let { id }: { id: string } = $props();
  let code = $state<string | null>(null);
  let err = $state(false);
  let run = $derived(store.checks.snippets?.[id]);
  let href = $derived(`./data/snippets/${id}.py`);
  let cmd = $derived(`uv run ${id}.py`);
  $effect(() => {
    // Ignore a reply that lands after the page has moved on (the prop may be gone by then).
    let live = true;
    code = null; err = false;
    fetch(`./data/snippets/${id}.py`).then((r) => (r.ok ? r.text() : Promise.reject()))
      .then((t) => { if (live) code = t; }).catch(() => { if (live) err = true; });
    return () => { live = false; };
  });

  // Just enough colour to tell comments and strings from code.
  type Tok = { t: string; k?: "c" | "s" };
  const RE = /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|f?"(?:\\.|[^"\\\n])*"|f?'(?:\\.|[^'\\\n])*')/g;
  function tokens(src: string): Tok[] {
    const out: Tok[] = [];
    let last = 0;
    for (const m of src.matchAll(RE)) {
      if (m.index > last) out.push({ t: src.slice(last, m.index) });
      out.push({ t: m[0], k: m[1] || m[0].startsWith('"""') || m[0].startsWith("'''") ? "c" : "s" });
      last = m.index + m[0].length;
    }
    out.push({ t: src.slice(last) });
    return out;
  }
  // The PEP 723 header is for uv, not for reading; show it folded.
  let parts = $derived.by(() => {
    if (!code) return null;
    const m = code.match(/^# \/\/\/ script\n[\s\S]*?\n# \/\/\/\n/);
    const head = m ? m[0] : "";
    const deps = head.match(/dependencies = \[(.*)\]/)?.[1].replace(/"/g, "").replace(/>=[^,\]]*/g, "") ?? "";
    return { head, deps, body: tokens(code.slice(head.length).replace(/^\n/, "")) };
  });
</script>

<section class="snip">
  <h3><Icon name="code" size={15} />Get the data in Python</h3>
  <p class="lead">Fetches a sample with UTC period-start stamps, units in the column names, and traps handled where code can.</p>
  {#if run}
    <p class="run" class:ok={run.result === "ok"} class:bad={run.result === "failed"}>
      {#if run.result === "ok"}
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="5" /></svg>
        Ran cleanly on {run.checked}{run.seconds != null ? ` in ${run.seconds} s` : ""}{#if run.summary}<span class="out">Last line printed: <code>{run.summary}</code></span>{/if}
      {:else if run.result === "failed"}
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><rect x="1.5" y="1.5" width="9" height="9" rx="1" /></svg>
        Failed on {run.checked}: <code>{run.error}</code>{#if run.last_ok}<span class="sub">{" · "}last ran cleanly {run.last_ok}</span>{/if}
      {:else}
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle class="ring" cx="6" cy="6" r="4" /></svg>
        Not run automatically: {run.reason}
      {/if}
    </p>
  {/if}
  {#if err}
    <p class="sub">The snippet could not be loaded. <a href="{REPO}/blob/main/snippets/{id}.py" target="_blank" rel="noopener">Open it on GitHub</a>.</p>
  {:else if !parts}
    <div class="skeleton"></div>
  {:else}
    <div class="codebox">
      <div class="bar">
        <span class="file">{id}.py</span>
        <span class="btns">
          <CopyButton text={code ?? ""} what="snippet" label="Copy code" />
          <a class="dl" href={href} download="{id}.py"><Icon name="download" size={14} />Download</a>
        </span>
      </div>
      {#if parts.head}<p class="deps">Needs Python 3.11, {parts.deps.split(",").map((d) => d.trim()).filter(Boolean).join(", ")} (declared for <code>uv</code>).</p>{/if}
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <pre tabindex="0" aria-label="Snippet code"><code>{#each parts.body as tk, i (i)}{#if tk.k}<span class={tk.k}>{tk.t}</span>{:else}{tk.t}{/if}{/each}</code></pre>
    </div>
    <div class="cmd"><code>{cmd}</code><CopyButton text={cmd} what="run command" label="Copy" /></div>
    <p class="how">With <a href="https://docs.astral.sh/uv/" target="_blank" rel="noopener">uv</a> installed, this installs the dependencies and runs it. All snippets: <a href="{REPO}/tree/main/snippets" target="_blank" rel="noopener">snippets/</a> on GitHub.</p>
  {/if}
</section>

<style>
  .snip { display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; }
  h3 { font-size: 14px; display: flex; align-items: center; gap: 7px; }
  .lead { font-size: 13px; color: var(--ink-2); }
  .run { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 6px; font-size: 12.5px; color: var(--ink-2); }
  .run svg { align-self: center; fill: var(--ink-3); }
  .run.ok svg { fill: var(--good); }
  .run.bad svg { fill: var(--bad); }
  .run .ring { fill: none; stroke: var(--ink-3); stroke-width: 1.5; }
  .run code { font-size: 12px; overflow-wrap: anywhere; }
  .codebox { border: 1px solid var(--line-strong); border-radius: var(--radius); background: var(--surface-2); overflow: hidden; }
  .bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px; padding: 6px 8px 6px 12px;
    border-bottom: 1px solid var(--line); background: var(--surface); }
  .file { font-family: var(--mono); font-size: 12px; color: var(--ink-2); overflow-wrap: anywhere; }
  .btns { display: flex; gap: 6px; }
  .dl { display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px; height: 26px; border: 1px solid var(--line-strong);
    border-radius: var(--radius-sm); background: var(--surface); font-size: 12.5px; font-weight: 500; color: var(--ink-2); text-decoration: none; }
  .dl:hover { color: var(--ink); border-color: var(--ink-3); }
  .deps { padding: 6px 12px 0; font-size: 12px; color: var(--ink-3); }
  pre { margin: 0; padding: 10px 12px 12px; overflow-x: auto; max-height: 440px; overflow-y: auto; font-size: 12px; line-height: 1.55; tab-size: 4; }
  pre code { font-size: inherit; }
  pre:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .c { color: var(--ink-3); font-style: italic; }
  .s { color: var(--accent-ink); }
  .out { flex-basis: 100%; padding-left: 18px; }
  .cmd { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 4px 4px 4px 12px;
    border: 1px solid var(--line-strong); border-radius: var(--radius-sm); background: var(--surface-2); }
  .cmd code { font-size: 12.5px; overflow-x: auto; white-space: nowrap; }
  .how { font-size: 12.5px; color: var(--ink-2); }
  .skeleton { height: 160px; border-radius: var(--radius); background: var(--surface-3); }
  .sub { color: var(--ink-3); }
</style>
