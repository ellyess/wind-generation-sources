# Adding or correcting an entry

One YAML file per source in `sources/`, named `<id>.yaml`. The schema is
`schema/source.schema.json`; `sources/dk-ens-turbine-register.yaml` is a worked example.
Run `uv run wgs validate` before opening a pull request.

## What belongs here

A dataset of **observed** wind power output: metered, settled, certified or reported by the
publisher. Simulated or modelled output (renewables.ninja, EMHIRES, C3S capacity factors,
satellite-derived estimates such as Climate TRACE) does not belong, however useful it is.
Restricted and commercial sources may be listed with `status: restricted`, so readers know they
exist and what they cost to use.

## The rules that keep it trustworthy

1. **Verify before you claim.** A field is filled from the publisher's own page, file or API,
   inspected on `last_checked`. If you could not check something, leave the optional field out
   or say so in `notes`. Never fill it from memory.
2. **A 200 response is not verification.** For per-plant or per-unit claims, request two
   different units, or two different years, and confirm the numbers differ. Some APIs ignore
   a filter and return the national series under per-plant column names (see
   `tr-epias-transparency.yaml`).
3. **Licences are read, not inferred.** Set `licence.verified: true` only after reading the
   terms on the publisher's own page, and give that page as `licence.url`. Until then,
   `redistribution` must be `unclear`. The validator enforces this.
4. **Every trap needs evidence**: a link to the publisher's documentation, an issue, a commit
   or an audit that shows the problem. A trap is a property of the source. A mistake that a
   client made while reading it is not a trap, unless the source makes it easy to make. Then
   write the summary so it says so.
5. **Dates are real dates.** `last_checked` is the day you checked; `found` on a trap is
   optional and only filled when you know it.
6. Write for someone who has never seen the source: plain English, no unexplained acronyms in
   summaries.

## Licence of this catalogue

Entries are CC-BY-4.0, code is MIT. The catalogue holds metadata and links only. It does not
re-host any publisher's data.
