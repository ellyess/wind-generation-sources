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
- **Machine-readable:** `catalogue.json` and `catalogue.csv`, published beside the site.
- **Raw:** one YAML file per source in [`sources/`](sources/). The schema is [`schema/source.schema.json`](schema/source.schema.json).

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

```sh
uv run wgs build --out site/dist
python3 -m http.server --directory site/dist 8000
```

## Licence

Catalogue entries are [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code is MIT. Fonts in `site/fonts/` (Barlow and IBM Plex Mono) are under the SIL Open Font License, included beside them. Each publisher's data stays under its own terms, as recorded in its entry.

Maintained by Ellyess Benmoufok. Many of the traps come from the validation audits of [PyVWF](https://github.com/ellyess/PyVWF).
