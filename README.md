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
