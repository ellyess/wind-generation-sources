# Snippets

One short Python script per catalogue entry, `snippets/<entry-id>.py`, that downloads a small
sample of that source's wind data and reads it correctly: the right time zone, the right end of
the period, the right unit, with the entry's traps handled. The site shows each one on its
source's page.

```sh
uv run snippets/gb-elexon-bmrs-fuel-type.py
```

Each script declares its own dependencies ([PEP 723](https://peps.python.org/pep-0723/)), so
`uv run` needs nothing installed first. Without uv, `pip install` the packages listed at the top
and run it with Python 3.11 or later.

## What every snippet does

- Fetches **one small sample** (a day, a month or one file), keyless, in under a minute.
- Ends with a pandas DataFrame `df` and prints it.
- For time series, `df` is indexed by **`time_utc`**: the start of each period, as a UTC
  timestamp, whatever the publisher uses. Converting from local time, period-end stamps or hour
  numbers happens in the snippet, where you can see it.
- A snippet converts only what its entry's `conventions` state. Where the time zone is
  `unknown`, `df` is indexed by a naive **`time`** as published, never labelled UTC. Where the
  stamp end is `unknown`, the stamp is kept as published, not shifted, so `time_utc` (or `time`)
  is then the published stamp rather than a known period start. The docstring says which, so the
  gap stays visible to whoever joins the data to weather.
- For statistics labelled by month or year, `df` is indexed by **`period`** (`2024-03`, `2024`).
- Column names carry the unit: `wind_mw` (average power over the period), `wind_mwh` (energy in
  the period), `wind_gwh`, `power_kw`, `capacity_mw`. Per-unit data stay long, with a `unit_id`
  column.
- Prints one line of context at the end (row count and a total), so a wrong unit shows up. Where
  the entry leaves the value type unknown, MW are not turned into energy: print the mean and peak
  MW instead of a total.
- Says in its docstring what the data are and which traps it handles, in plain words.

## Header markers

Optional comment lines straight after the docstring, read by the checker:

- `# wgs: needs ENV_VAR` – the source needs a free key; the script reads it from that
  environment variable, and the checker skips it when the variable is not set.
- `# wgs: skip <reason>` – the checker does not run it (for example, the smallest file is
  1.2 GB). Use this only when there is no smaller sample.

## Checking

```sh
uv run wgs check snippets              # run every snippet, write checks/snippets.json
uv run wgs check snippets --only be-elia-wind-production
```

The result, and the date each snippet last ran cleanly, is shown on the site. A snippet that
fails is shown with the failure, not hidden.

## Rules

Keyless public access only; no scraping behind logins or bot checks, and no spoofed user
agents. Do not hard-code keys. Do not write files outside a temporary directory. Keep each script
under about 60 lines and readable by someone who knows a little pandas.
