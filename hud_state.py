"""
hud_state.py — Thread-safe shared state between brain.py and the HUD.
Both processes communicate via a small JSON file on disk.
This avoids any IPC complexity and works across threads or processes.
"""

import json
import os
import threading

import os
STATE_FILE = os.path.join(os.path.dirname(__file__), "jarvis_hud_state.json")
_lock = threading.Lock()

DEFAULT_STATE = {
    "time": "",
    "weather": {
        "temp": "--",
        "condition": "--",
        "icon": "clear"          # clear | clouds | rain | thunder | snow | mist
    },
    "spotify": {
        "playing": False,
        "track": "--",
        "artist": "--",
        "progress_ms": 0,
        "duration_ms": 1,
        "album_art_url": ""
    },
    "jarvis_state": "idle",      # idle | listening | thinking | speaking | whispering
    "waveform": []               # list of floats 0.0–1.0, updated while speaking
}

def write_state(updates: dict):
    """Merge `updates` into the current state and persist to disk."""
    with _lock:
        state = _read_raw()
        _deep_merge(state, updates)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)

def read_state() -> dict:
    """Return the current full state dict."""
    with _lock:
        return _read_raw()

def _read_raw() -> dict:
    if not os.path.exists(STATE_FILE):
        return dict(DEFAULT_STATE)
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        # Fill in any missing keys from defaults
        merged = dict(DEFAULT_STATE)
        _deep_merge(merged, data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_STATE)

def _deep_merge(base: dict, override: dict):
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
