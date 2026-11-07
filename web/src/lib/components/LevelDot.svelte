<script lang="ts">
  let { tier, size = 10 }: { tier: number; size?: number } = $props();
</script>

<i class="dot" style:--c="var(--l{tier})" style:width="{size}px" style:height="{size}px" aria-hidden="true"></i>

<style>
  .dot {
    display: inline-block; flex: none; border-radius: 2px; background: var(--c);
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ink) 10%, transparent);
  }
</style>
