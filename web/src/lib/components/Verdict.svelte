<script lang="ts">
  import { REUSE_TONE, TEXT } from "../text";
  // Licence verdict: a shaped mark plus the words, so the meaning never rests on colour.
  let { value }: { value: string } = $props();
  let tone = $derived(REUSE_TONE[value] ?? "none");
</script>

<span class="verdict t-{tone}">
  <svg viewBox="0 0 10 10" width="10" height="10" aria-hidden="true">
    {#if tone === "good"}<circle cx="5" cy="5" r="4.2" />
    {:else if tone === "warn" || tone === "serious"}<path d="M5 .8 9.4 9H.6z" />
    {:else if tone === "bad"}<rect x="1" y="1" width="8" height="8" rx="1" />
    {:else}<circle cx="5" cy="5" r="3.6" fill="none" stroke-width="1.4" />{/if}
  </svg>{TEXT.reuse[value] ?? value}
</span>

<style>
  .verdict { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
  svg { flex: none; }
  .t-good svg { fill: var(--good-dot); }
  .t-warn svg { fill: var(--warn-dot); }
  .t-serious svg { fill: var(--serious-dot); }
  .t-bad svg { fill: var(--bad-dot); }
  .t-none svg { stroke: var(--none-dot); }
</style>
