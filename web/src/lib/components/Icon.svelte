<script lang="ts">
  // One stroke family (1.5px, round caps) for every icon on the page.
  let { name, size = 16 }: { name: string; size?: number } = $props();
  const P: Record<string, string> = {
    out: "M9 3.5h3.5V7 M12.5 3.5 7 9 M11 9.5v3H3.5V5h3",
    copy: "M5.5 5.5h7v7h-7z M10.5 5.5v-2h-7v7h2",
    check: "m3.5 8.5 3 3 6-7",
    back: "M10 3.5 5.5 8l4.5 4.5",
    chev: "M6 3.5 10.5 8 6 12.5",
    close: "M4 4l8 8M12 4l-8 8",
    search: "M7 12A5 5 0 1 0 7 2a5 5 0 0 0 0 10z M10.6 10.6 14 14",
    sun: "M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M8 1.5v1.2 M8 13.3v1.2 M1.5 8h1.2 M13.3 8h1.2 M3.4 3.4l.85.85 M11.75 11.75l.85.85 M3.4 12.6l.85-.85 M11.75 4.25l.85-.85",
    moon: "M13 9.5A5.5 5.5 0 0 1 6.5 3a5.5 5.5 0 1 0 6.5 6.5z",
    globe: "M8 14.5a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13z M1.5 8h13 M8 1.5c2 2 2.6 4.3 2.6 6.5S10 12.5 8 14.5C6 12.5 5.4 10.2 5.4 8S6 3.5 8 1.5",
    flat: "M1.5 3.5h13v9h-13z M1.5 8h13 M6 3.5v9 M10 3.5v9",
    trap: "M8 2 14.5 13.5h-13z M8 6.5v3.2 M8 11.6v.1",
    download: "M8 2.5v7.5 M4.5 7 8 10.5 11.5 7 M3 13.5h10",
    code: "M5.5 4.5 2 8l3.5 3.5 M10.5 4.5 14 8l-3.5 3.5",
    filter: "M2 3.5h12 M4.5 8h7 M6.5 12.5h3",
    live: "M2 9.5h2.5L6 5l3 7 1.6-3.5H14",
  };
</script>

<svg class="ic" width={size} height={size} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
  <path d={P[name]} fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
</svg>

<style>
  .ic { flex: none; display: inline-block; vertical-align: -0.18em; }
</style>
