# E-ink dashboard refactor + richer layout

## Goal
One 800×480 e-ink image composed from independent sources, built to iterate cheaply.
Sources: two Garmin accounts (resting HR + sleep score), 5-day weather (in header),
random daily quote (multi-line, half-width square block).

## Design principles
- **Layout is config, not code.** All panel rectangles live in `config.py` (`LAYOUT`).
- **Panels are isolated.** Each `draw_x(draw, box, data, fonts)` paints only inside its box.
- **DEBUG_BOXES** flag outlines + labels every region for fast visual iteration.
- **Weather icons are drawn vectors** (sun/cloud/rain), not emoji — DejaVu on CI can't render emoji.

## Structure
- [x] `config.py` — dims, PEOPLE, LOCATION, paths, LAYOUT boxes, DEBUG_BOXES
- [x] `fonts.py` — shared `load_fonts()`
- [x] `icons.py` — `draw_weather_icon(draw, box, kind, fonts?)` for sun/cloud/rain
- [x] `sources/weather.py` — fetch + parse → {today, forecast[4]}, code→icon bucket
- [x] `sources/garmin.py` — parameterized per person → {name, resting_hr, sleep_score}
- [x] `sources/quote.py` — random entry from blank-line-separated `quotes.txt`
- [x] `panels/header.py` — date + today weather inline + forecast strip
- [x] `panels/health.py` — two people stacked: resting HR, sleep score
- [x] `panels/quote.py` — word-wrapped multi-line block, centered
- [x] `dashboard.py` — orchestrate: fetch all → compose → save PNG (+ debug grid)
- [x] `quotes.txt` — sample, blank-line separated
- [x] Update `.github/workflows/dashboard.yml` → `python dashboard.py`, 2nd Garmin secret set
- [x] Delete absorbed `ga.py`, `weather.py`

## Verify
- [x] Render with mock data (no creds) → confirms layout/panels don't crash
- [x] DEBUG_BOXES render → confirms regions
- [ ] Live run with real creds (user does this locally — needs GARMIN_*_H/_W)

## Review
- Split monolithic `ga.py`/`weather.py` into config + fonts + icons + sources/ +
  panels/ + `dashboard.py`. Layout is now config-driven (`LAYOUT` tuples), each
  panel isolated to its box. `DEBUG_BOXES` overlays the region grid for iteration.
- Two Garmin accounts via `config.PEOPLE` (env-var driven, suffix _H / _W).
  Health panel shows resting HR + sleep score; `METRICS` list makes adding more
  a one-liner. Sleep score tried across two known API paths, "—" when absent.
- Weather moved into the header (today inline + N-day strip). 3-icon buckets
  drawn as FILLED vectors (not emoji — DejaVu on CI can't render emoji).
- Quote: random blank-line-separated entry, word-wrapped + auto font-shrink,
  centered in the left square block.
- Workflow runs `python dashboard.py`, publishes `dashboard.png`, uses
  `GARMINTOKENS_H` / `GARMINTOKENS_W` secrets. README + requirements updated.
- Verified: mock render (normal + DEBUG_BOXES), icon rework, all modules compile,
  import wiring + weather buckets + quote parse from project root.
- Remaining (user, needs creds): live run with both Garmin accounts + add the two
  CI secrets. Confirm the sleep-score field path matches their accounts' data.
