"""
computer_control.py — Jarvis keyboard and mouse automation module.
Handles opening apps, screenshots, volume, web search, and site-specific search.

INSTALL:
    pip install pyautogui pynput
"""

import subprocess
import os
import time
import pyautogui
import webbrowser
from urllib.parse import quote

# Disable pyautogui failsafe (moving mouse to corner won't crash it)
pyautogui.FAILSAFE = False

# ── APP LAUNCHER ─────────────────────────────────────────────────────────────
APP_MAP = {
    "firefox":       "firefox",
    "browser":       "firefox",
    "chrome":        "chromium-browser",
    "chromium":      "chromium-browser",
    "terminal":      "lxterminal",
    "files":         "pcmanfm",
    "file manager":  "pcmanfm",
    "spotify":       "spotify",
    "calculator":    "galculator",
    "text editor":   "mousepad",
    "notepad":       "mousepad",
    "vscode":        "code",
    "vs code":       "code",
    "code":          "code",
}

def open_app(command_text):
    """Opens an application by name."""
    cmd = command_text.lower()
    for keyword, app in APP_MAP.items():
        if keyword in cmd:
            try:
                subprocess.Popen([app])
                return f"Opening {keyword}, sir."
            except FileNotFoundError:
                return f"I couldn't find {keyword} installed on this system, sir."
    return "I don't recognise that application, sir."


# ── SCREENSHOT ────────────────────────────────────────────────────────────────
SCREENSHOT_DIR = os.path.expanduser("~/Pictures/jarvis_screenshots")

def take_screenshot():
    """Takes a screenshot and saves it to ~/Pictures/jarvis_screenshots/."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filename = f"screenshot_{int(time.time())}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    pyautogui.screenshot(filepath)
    return f"Screenshot saved as {filename}, sir."


# ── VOLUME CONTROL ────────────────────────────────────────────────────────────
def set_volume(command_text):
    """Controls system volume via amixer (works on all Pi OS versions)."""
    cmd = command_text.lower()

    if "mute" in cmd:
        subprocess.run(["amixer", "-q", "sset", "Master", "mute"])
        return "Audio muted, sir."

    if "unmute" in cmd or "un-mute" in cmd:
        subprocess.run(["amixer", "-q", "sset", "Master", "unmute"])
        return "Audio restored, sir."

    if "max" in cmd or "full" in cmd:
        subprocess.run(["amixer", "-q", "sset", "Master", "100%", "unmute"])
        return "Volume set to maximum, sir."

    # Extract a percentage if spoken ("set volume to 50")
    import re
    match = re.search(r'(\d+)', cmd)
    if match:
        level = max(0, min(100, int(match.group(1))))
        subprocess.run(["amixer", "-q", "sset", "Master", f"{level}%", "unmute"])
        return f"Volume set to {level} percent, sir."

    if "up" in cmd or "increase" in cmd or "louder" in cmd:
        subprocess.run(["amixer", "-q", "sset", "Master", "10%+", "unmute"])
        return "Volume increased, sir."

    if "down" in cmd or "decrease" in cmd or "lower" in cmd or "quieter" in cmd:
        subprocess.run(["amixer", "-q", "sset", "Master", "10%-"])
        return "Volume decreased, sir."

    return "I didn't catch a volume level, sir."


# ── WEB SEARCH ────────────────────────────────────────────────────────────────
# Maps spoken site names to their search URL templates
SITE_SEARCH_MAP = {
    "youtube":   "https://www.youtube.com/results?search_query={query}",
    "google":    "https://www.google.com/search?q={query}",
    "reddit":    "https://www.reddit.com/search/?q={query}",
    "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search={query}",
    "github":    "https://github.com/search?q={query}",
    "amazon":    "https://www.amazon.com/s?k={query}",
    "twitter":   "https://twitter.com/search?q={query}",
    "x":         "https://twitter.com/search?q={query}",
    "spotify":   "https://open.spotify.com/search/{query}",
    "imdb":      "https://www.imdb.com/find?q={query}",
    "stackoverflow": "https://stackoverflow.com/search?q={query}",
    "maps":      "https://www.google.com/maps/search/{query}",
    "google maps": "https://www.google.com/maps/search/{query}",
}

def web_search(command_text):
    """
    Handles general and site-specific searches.
    Examples:
      "search for black holes"
      "search for coding tutorials on YouTube"
      "search for python on GitHub"
      "look up Albert Einstein on Wikipedia"
    """
    import re
    cmd = command_text.lower()

    # Strip trigger phrases to isolate the query
    for phrase in ["search for", "search", "look up", "find", "google", "show me"]:
        if phrase in cmd:
            cmd = cmd.replace(phrase, "", 1).strip()
            break

    # Check for site-specific intent ("on YouTube", "on Reddit", etc.)
    target_site = None
    target_url  = None

    for site, url_template in SITE_SEARCH_MAP.items():
        patterns = [f"on {site}", f"in {site}", f"from {site}", f"using {site}"]
        for pattern in patterns:
            if pattern in cmd:
                cmd         = cmd.replace(pattern, "").strip()
                target_site = site
                target_url  = url_template
                break
        if target_site:
            break

    # Also handle "YouTube videos about X" style phrasing
    youtube_patterns = ["videos about", "videos on", "video about", "video on",
                        "clips of", "clips about"]
    for pattern in youtube_patterns:
        if pattern in cmd:
            cmd        = cmd.replace(pattern, "").strip()
            target_site = "youtube"
            target_url  = SITE_SEARCH_MAP["youtube"]
            break

    query = cmd.strip()
    if not query:
        return "What would you like me to search for, sir?"

    encoded = quote(query)

    if target_url:
        url = target_url.replace("{query}", encoded)
        webbrowser.open(url)
        return f"Searching {target_site} for '{query}', sir."
    else:
        # Default to Google
        url = f"https://www.google.com/search?q={encoded}"
        webbrowser.open(url)
        return f"Searching the web for '{query}', sir."


# ── MAIN HANDLER (called by brain.py) ────────────────────────────────────────
def handle_computer_command(command_text):
    """
    Routes computer control commands to the right function.
    Called from brain.py's process_command().
    """
    cmd = command_text.lower()

    # Screenshot
    if any(w in cmd for w in ["screenshot", "screen shot", "capture screen", "take a picture of the screen"]):
        return take_screenshot()

    # Volume
    if any(w in cmd for w in ["volume", "mute", "unmute", "louder", "quieter"]):
        return set_volume(cmd)

    # Web search
    if any(w in cmd for w in ["search for", "search", "look up", "google", "find me", "show me"]):
        return web_search(cmd)

    # Open app
    if any(w in cmd for w in ["open", "launch", "start", "run"]):
        return open_app(cmd)

    return None   # Not a computer command — let brain.py fall through to AI
