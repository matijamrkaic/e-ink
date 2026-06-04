E-ink dashboards sized for a 7.5" Waveshare display (800×480). Each script
fetches data, draws a PNG preview, and opens it in Preview on macOS.

## Install dependencies (once)
```bash
pip3 install requests Pillow garminconnect
```

## Weather dashboard
```bash
python3 weather.py
```
Pulls current conditions + a 3-day forecast from Open-Meteo (no API key needed).
Edit `LATITUDE` / `LONGITUDE` / `CITY_NAME` at the top of `weather.py` to change
location.

## Garmin daily stats
```bash
export GARMIN_EMAIL="you@example.com"
export GARMIN_PASSWORD="your-password"
python3 ga.py
```
Logs into Garmin Connect, shows today's steps (with goal progress), resting HR,
sleep, calories, stress, body battery, and a 7-day step bar chart. OAuth tokens
are cached in `~/.garminconnect` so subsequent runs skip the password
round-trip.

## Automated hosting (GitHub Actions → GitHub Pages)
`.github/workflows/dashboard.yml` regenerates the image every 12 hours and
publishes it to GitHub Pages, so the e-ink device just fetches a fixed URL:

```
https://matijamrkaic.github.io/e-ink/garmin_preview.png
```

### One-time setup
1. **Generate auth tokens locally** (datacenter logins trip Garmin's MFA, so CI
   reuses a saved token string instead of logging in each run):
   ```bash
   export GARMIN_EMAIL="you@example.com"
   export GARMIN_PASSWORD="your-password"
   python3 ga.py
   ```
   Every local run prints a one-line `GARMINTOKENS` string (a live credential —
   keep it secret).
2. **Add the secret:** repo → Settings → Secrets and variables → Actions → New
   repository secret, name `GARMINTOKENS`, paste the whole one-line string.
   *(Optional fallback: also add `GARMIN_EMAIL` / `GARMIN_PASSWORD` secrets.)*
3. **Enable Pages:** repo → Settings → Pages → Source = **GitHub Actions**.
4. Trigger once from the **Actions** tab (Run workflow) to verify.

The token auto-refreshes on each run, but if auth eventually starts failing,
re-run step 1 and update the `GARMINTOKENS` secret.

### On the microcontroller
GitHub Pages is served via a CDN that caches for a few minutes, so add a
cache-buster when fetching, e.g.
`https://matijamrkaic.github.io/e-ink/garmin_preview.png?t=<unix-time>`.

## What changes for the ESP32 later
When you're ready to flash it, you'll only swap `save_and_preview()` for
something like:
```python
def send_to_eink(img):
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.display(epd.getbuffer(img))
    epd.sleep()
```
