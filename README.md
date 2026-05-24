1. Install dependencies (once):
```bash
pip3 install requests Pillow
```
2. Run it:
```bash
python3 weather.py
```


### What changes for the ESP32 later
When you're ready to flash it, you'll only swap save_and_preview() for something like:
```python
def send_to_eink(img):
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.display(epd.getbuffer(img))
    epd.sleep()
```
