"""
hud_services.py — Background threads that keep HUD data fresh.
Polls weather every 10 minutes and Spotify every 3 seconds.
Run these threads from brain.py alongside your existing threads.

SETUP:
  pip install requests spotipy

  Add these to your environment or a config.py:
    OPENWEATHER_API_KEY = "your_key"   # free tier at openweathermap.org
    SPOTIFY_CLIENT_ID   = "your_id"
    SPOTIFY_CLIENT_SECRET = "your_secret"
    SPOTIFY_REDIRECT_URI  = "http://localhost:8888/callback"
    LAT = 30.3322   # Jacksonville, FL — change to yours
    LON = -81.6557
"""

import time
import math
import threading
import requests
import json
import os

from hud_state import write_state

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
# Edit these or import from a separate config.py
try:
    from config import (
        OPENWEATHER_API_KEY,
        SPOTIFY_CLIENT_ID,
        SPOTIFY_CLIENT_SECRET,
        SPOTIFY_REDIRECT_URI,
        LAT, LON
    )
except ImportError:
    OPENWEATHER_API_KEY   = os.getenv("OPENWEATHER_API_KEY", "")
    SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    SPOTIFY_REDIRECT_URI  = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
    LAT = float(os.getenv("LAT", "30.3322"))
    LON = float(os.getenv("LON", "-81.6557"))

# ── WEATHER ───────────────────────────────────────────────────────────────────
_OWM_ICON_MAP = {
    "01": "clear", "02": "clouds", "03": "clouds", "04": "clouds",
    "09": "rain",  "10": "rain",   "11": "thunder",
    "13": "snow",  "50": "mist"
}

def _owm_icon(icon_code: str) -> str:
    return _OWM_ICON_MAP.get(icon_code[:2], "clear")

def weather_loop():
    """Poll OpenWeatherMap every 10 minutes."""
    while True:
        try:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={LAT}&lon={LON}&appid={OPENWEATHER_API_KEY}&units=imperial"
            )
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                temp   = round(data["main"]["temp"])
                cond   = data["weather"][0]["main"]
                icon   = _owm_icon(data["weather"][0]["icon"])
                write_state({"weather": {"temp": f"{temp}°F", "condition": cond, "icon": icon}})
        except Exception as e:
            print(f"[HUD/weather] {e}")
        time.sleep(600)   # 10 minutes


# ── SPOTIFY ───────────────────────────────────────────────────────────────────
import spotipy
from spotipy.oauth2 import SpotifyOAuth

_sp = None
_sp_lock = threading.Lock()

def _get_spotify():
    global _sp
    with _sp_lock:
        if _sp is None:
            _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope="user-read-playback-state user-read-currently-playing user-modify-playback-state"
            ))
        return _sp

def spotify_loop():
    """Poll Spotify every 3 seconds and push now-playing state."""
    while True:
        try:
            sp = _get_spotify()
            pb = sp.current_playback()
            if pb and pb.get("is_playing"):
                item = pb["item"]
                write_state({"spotify": {
                    "playing":      True,
                    "track":        item["name"],
                    "artist":       ", ".join(a["name"] for a in item["artists"]),
                    "progress_ms":  pb["progress_ms"],
                    "duration_ms":  item["duration_ms"],
                    "album_art_url": item["album"]["images"][0]["url"] if item["album"]["images"] else ""
                }})
            else:
                write_state({"spotify": {"playing": False, "track": "--", "artist": "--",
                                         "progress_ms": 0, "duration_ms": 1}})
        except Exception as e:
            print(f"[HUD/spotify] {e}")
        time.sleep(3)


# ── WAVEFORM GENERATOR ────────────────────────────────────────────────────────
# Since pyttsx3 doesn't expose PCM directly, we synthesize a plausible
# animated waveform while Jarvis is speaking, keyed on jarvis_state.
_waveform_thread_active = False

def waveform_loop():
    """Animate the waveform bars while Jarvis is speaking/whispering."""
    import random
    phase = 0.0
    while True:
        from hud_state import read_state
        state = read_state()
        js = state.get("jarvis_state", "idle")

        if js in ("speaking", "thinking"):
            # Lively sine-based waveform with noise
            bars = []
            for i in range(32):
                val = (math.sin(phase + i * 0.4) * 0.5 + 0.5)
                val += random.uniform(-0.15, 0.15)
                val = max(0.05, min(1.0, val))
                bars.append(round(val, 3))
            write_state({"waveform": bars})
            phase += 0.25
        elif js == "whispering":
            bars = [round(max(0.02, min(0.25, 0.1 + random.uniform(-0.05, 0.05))), 3)
                    for _ in range(32)]
            write_state({"waveform": bars})
        else:
            # Flatline
            write_state({"waveform": [0.03] * 32})

        time.sleep(0.05)   # 20 fps waveform update


# ── PUBLIC: launch all service threads ───────────────────────────────────────
def start_hud_services():
    """Call this once from brain.py __main__ to start all background threads."""
    threads = [
        threading.Thread(target=weather_loop,   daemon=True, name="hud-weather"),
        threading.Thread(target=spotify_loop,   daemon=True, name="hud-spotify"),
        threading.Thread(target=waveform_loop,  daemon=True, name="hud-waveform"),
    ]
    for t in threads:
        t.start()
    print("[HUD] Service threads started.")
