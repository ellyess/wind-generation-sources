<script lang="ts">
  import { shortLink } from "../text";
  import Icon from "./Icon.svelte";
  let { href, label = "" }: { href: string; label?: string } = $props();
</script>

<a class="ext" {href} target="_blank" rel="noopener">{label || shortLink(href)}<Icon name="out" size={13} /></a>

<style>
  .ext { display: inline; overflow-wrap: anywhere; }
  .ext :global(.ic) { margin-left: 3px; opacity: 0.7; }
</style>
