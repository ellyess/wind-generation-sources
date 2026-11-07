# Wind Generation Sources

An open catalogue of where to find **observed** wind power generation data, worldwide.

Each entry records:
- what the data are, and at what level and time step;
- how to get them;
- whether you may re-host them;
- the known traps, each with a link to the evidence.

Every licence is read on the publisher's own page and dated. Until it has been read, re-hosting stays "unclear". Simulated or modelled output (renewables.ninja, EMHIRES, capacity factors from reanalysis) is left out on principle.

The catalogue holds metadata and links only. It never re-hosts a publisher's data.

## Use it

- **Browse:** the site, built from this repository by GitHub Actions and served on GitHub Pages.
- **Machine-readable:** `catalogue.json` and `catalogue.csv`, published with the site under `data/`.
- **Code:** a short Python script per source in [`snippets/`](snippets/) that downloads a sample
  and reads it correctly: UTC period starts, units in the column names, traps handled. Run one
  with `uv run snippets/<id>.py`.
- **Raw:** one YAML file per source in [`sources/`](sources/). The schema is [`schema/source.schema.json`](schema/source.schema.json).

## How it is checked

Four checks run by machine, weekly in CI and on demand:

```sh
uv run wgs check links            # request every link again
uv run wgs check totals --year 2024   # sum a year from each keyless source and compare
uv run wgs check snippets         # run every snippet against the live source
```

- **Links.** Every access, documentation, licence, evidence and tool link is requested. A link
  that refuses automated clients is reported as not checked, never as working. Trap evidence
  that is meant to fail (a 404 for a missing year) carries `evidence_is_error: true`; if it
  starts loading, the trap is flagged for a recheck.
- **Annual totals.** Where a source can be read without a key, one calendar year of wind
  output is summed from its own data and compared with a reference: a national publisher's
  figure for the whole wind fleet in that calendar year where there is one
  (`checks/national-figures-2024.yaml` lists each with its quoted source), otherwise Eurostat's
  gross electricity production, otherwise Ember's. Within 15% agrees and within 30% is noted, the bands
  used in the PyVWF scorecard audit. Gross production runs above what grid operators meter,
  so a ratio a little under 1 is normal.
- **Time step.** The interval count in that year is compared with the time step the entry
  states.
- **Snippets.** Every snippet is run against the live source. The site shows the date each
  one last ran cleanly, or the error if it failed.

Results are committed to [`checks/`](checks/) and shown in each entry on the site. Entries
compiled by an automated research pass carry `reviewed: false` and are marked *Unreviewed*
until a person has checked them.

## Cite it

See [`CITATION.cff`](CITATION.cff).

## Add or correct a source

Edit or add one file in `sources/`, then check it:

```sh
uv sync
uv run wgs validate
```

Open a pull request. [CONTRIBUTING.md](CONTRIBUTING.md) sets out the rules:
- verify every field before you claim it;
- check per-unit claims with two different units or years;
- read licences, never infer them;
- give every trap evidence.

The validator enforces the rules it can.

## Build the site locally

The site is a Svelte app in `web/`, built with Vite. `wgs build` writes the data files it reads
into `web/public/data/`.

```sh
uv run wgs build
cd web && npm ci && npm run dev
```

`npm run build` writes the static site to `web/dist/`, which GitHub Pages serves. The map uses
MapLibre GL with OpenFreeMap tiles; no key is needed. Live charts are requested by the visitor's
browser from publishers that allow it (Elexon, RTE via ODRÉ, Elia, SMARD, REE and Eurostat), and
nothing is stored.

## Licence

Catalogue entries are [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code is MIT. The Inter typeface is under the SIL Open Font License. Each publisher's data stays under its own terms, as recorded in its entry.

Maintained by Ellyess Benmoufok. Many of the traps come from the validation audits of [PyVWF](https://github.com/ellyess/PyVWF).
