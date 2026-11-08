<script lang="ts">
  import Icon from "./Icon.svelte";
  let { text, what, label = "Copy" }: { text: string; what: string; label?: string } = $props();
  let state = $state<"idle" | "done" | "fail">("idle");
  let timer: ReturnType<typeof setTimeout> | undefined;
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      state = "done";
    } catch {
      state = "fail";
    }
    clearTimeout(timer);
    timer = setTimeout(() => (state = "idle"), 1600);
  }
</script>

<button type="button" class="copy" class:done={state === "done"} onclick={copy}>
  <Icon name={state === "done" ? "check" : "copy"} size={14} />
  <span aria-live="polite">{state === "done" ? "Copied" : state === "fail" ? "Copy failed" : label}</span>{#if label === "Copy"}<span class="visually-hidden"> {what}</span>{/if}
</button>

<style>
  .copy {
    display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px; height: 26px;
    border: 1px solid var(--line-strong); border-radius: var(--radius-sm); background: var(--surface);
    font-size: 12.5px; font-weight: 500; color: var(--ink-2); white-space: nowrap;
  }
  .copy:hover { color: var(--ink); border-color: var(--ink-3); }
  .copy.done { color: var(--ink); border-color: var(--line-strong); }
</style>
