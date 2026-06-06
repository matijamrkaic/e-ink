A family e-ink dashboard sized for a 7.5" Waveshare display (800×480). One run
fetches every data source, composes them onto a single PNG, and (via GitHub
Actions) publishes it to a fixed URL the device fetches.

## What's on it
- **Header** — today's date, today's weather (icon + high/low), and a strip of
  the next few days. Weather icons are drawn as vectors (sun / cloud / rain), so
  they render identically on macOS and the CI runner.
- **Quote** — a random multi-line quote from `quotes.txt` (entries separated by
  a blank line), wrapped and centered in the left block.
- **Health** — one column per person in `config.PEOPLE` (two Garmin accounts):
  resting HR + sleep score, a GitHub-style 30-day activity grid (a dot on every
  day with a logged workout) beside a count of each activity type, and a 7-day
  daily-steps bar chart.

## How it's organized
The layout is **data, not code** — every panel is a named rectangle in
`config.py` (`LAYOUT`). To move or resize a panel, edit one tuple; no drawing
code changes. Set `DEBUG_BOXES = True` in `config.py` to overlay each region's
outline + label while you iterate.

```
dashboard.py        entry point: fetch all sources → compose canvas → save PNG
config.py           display size, PEOPLE, location, paths, LAYOUT, DEBUG_BOXES
fonts.py            shared font loading — JetBrains Mono, weight-aware
assets/fonts/       bundled OFL TTFs — identical rendering locally and on CI
icons.py            vector weather icons (sun / cloud / rain)
grid.py             activity dot grid + 7-day steps bar chart
sources/            one module per data source, each returns a clean dict
  weather.py          Open-Meteo (no API key)
  garmin.py           per-person resting HR + sleep score (parameterized)
  quote.py            random entry from quotes.txt
panels/             one module per region, each draws inside its box
  header.py  health.py  quote.py
quotes.txt          manually filled; blank line between entries
```

To **add a data source**: drop a `sources/x.py`, a `panels/x.py`, and one box
in `LAYOUT`, then wire it in `dashboard.py`.

## Run locally
```bash
python3 -m venv .venv                    # create a virtual environment (once)
source .venv/bin/activate                # activate it (re-run in each new shell)
pip install -r requirements.txt          # garminconnect + Pillow + requests + python-dotenv

cp .env.example .env                     # then fill in your two Garmin logins
python dashboard.py                      # writes dashboard.png
```
The `.venv` keeps dependencies isolated from your system Python. Activate it in
any new terminal (`source .venv/bin/activate`) before running the scripts.
`config.py` auto-loads `.env` (gitignored), so credentials are set once and
`python3 dashboard.py` just works — no re-exporting per shell. The vars are
`GARMIN_EMAIL_H` / `GARMIN_PASSWORD_H` (husband) and `..._W` (wife); exporting
them in your shell instead works too.

OAuth tokens are cached per person in `~/.garminconnect_h` / `~/.garminconnect_w`
so subsequent runs skip the password round-trip. Edit `LATITUDE` / `LONGITUDE` /
`TIMEZONE` in `config.py` to change the weather location.

## Iterate on the layout (offline, no Garmin)
When you're tweaking panels or `LAYOUT`, you don't want to hit Garmin/weather on
every run. Use the fixture-based preview — it renders instantly with no network:
```bash
python3 preview.py            # render dashboard.png from sample data
python3 preview.py --debug    # overlay the LAYOUT region grid (= config.DEBUG_BOXES)
```
Keep `dashboard.png` open in Preview; it auto-reloads each time you re-run.

## Automated hosting (GitHub Actions → GitHub Pages)
`.github/workflows/dashboard.yml` regenerates the image **3× a day** — at
**08:00, 12:00, and 20:00 Europe/Berlin** — and publishes it to GitHub Pages, so
the e-ink device just fetches a fixed URL:

```
https://matijamrkaic.github.io/e-ink/dashboard.png
```

GitHub cron runs in UTC and ignores DST, so the workflow fires at both the
winter and summer candidate hours and a small `gate` job drops the runs that
aren't 08/12/20 in Berlin — giving the right local times year-round.

### One-time setup
1. **Make the repo public.** GitHub Pages only serves private repos on paid
   plans, so on the Free plan flip this repo to public:
   Settings → General → Danger Zone → Change visibility → Public.
2. **Generate auth tokens locally for each account** (datacenter logins trip
   Garmin's MFA, so CI reuses a saved token string instead of logging in):
   ```bash
   export GARMIN_EMAIL_H="him@example.com" GARMIN_PASSWORD_H="..."
   export GARMIN_EMAIL_W="her@example.com" GARMIN_PASSWORD_W="..."
   python3 dashboard.py
   ```
   The run prints a one-line token blob per person (a live credential — keep it
   secret).
3. **Add the secrets:** repo → Settings → Secrets and variables → Actions → New
   repository secret. Create `GARMINTOKENS_H` and `GARMINTOKENS_W`, pasting each
   person's one-line token string.
4. **Enable Pages:** repo → Settings → Pages → Source = **GitHub Actions**.
5. Trigger once from the **Actions** tab (Run workflow) to verify.

Tokens auto-refresh on each run, but if auth eventually starts failing, re-run
step 2 and update the secrets.

### On the microcontroller
GitHub Pages is served via a CDN that caches for a few minutes, so add a
cache-buster when fetching, e.g.
`https://matijamrkaic.github.io/e-ink/dashboard.png?t=<unix-time>`.

## What changes for the ESP32 later
When you're ready to flash it, swap the `img.save(...)` in `dashboard.py` for
something like:
```python
def send_to_eink(img):
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.display(epd.getbuffer(img))
    epd.sleep()
```
