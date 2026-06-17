"""
alarm_briefing.py — Alarm, morning briefing, and schedule module for Jarvis.

Features:
  - Set alarms by voice ("Jarvis, set an alarm for 7am")
  - Cancel alarms by voice ("Jarvis, cancel my alarm")
  - Morning briefing: weather + today's Google Calendar events + a daily joke
  - Three beeps followed by Jarvis speaking when alarm fires

INSTALL:
    pip install google-auth-oauthlib google-api-python-client requests
"""

import voice_output
import os
import time
import threading
import datetime
import json
import re
import requests
import numpy as np
import sounddevice as sd

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE       = os.path.join(BASE_DIR, "token.json")
ALARMS_FILE      = os.path.join(BASE_DIR, "alarms.json")
SCOPES           = ["https://www.googleapis.com/auth/calendar.readonly"]

# Weather config — reads from .env via brain.py's load_dotenv
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
LAT = os.getenv("LAT", "30.3322")
LON = os.getenv("LON", "-81.6557")


# ── GOOGLE CALENDAR AUTH ──────────────────────────────────────────────────────
def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


# ── GOOGLE CALENDAR EVENTS ────────────────────────────────────────────────────
def get_todays_events():
    """Returns a list of today's calendar events as readable strings."""
    try:
        service = get_calendar_service()
        now     = datetime.datetime.utcnow()
        start   = datetime.datetime(now.year, now.month, now.day, 0, 0, 0).isoformat() + "Z"
        end     = datetime.datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return ["No events scheduled for today, sir."]

        summaries = []
        for event in events:
            title = event.get("summary", "Unnamed event")
            start_raw = event["start"].get("dateTime", event["start"].get("date"))
            if "T" in start_raw:
                dt = datetime.datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                local_dt = dt.astimezone()
                time_str = local_dt.strftime("%I:%M %p").lstrip("0")
                summaries.append(f"{title} at {time_str}")
            else:
                summaries.append(f"{title} — all day")
        return summaries

    except Exception as e:
        print(f"[CALENDAR ERROR] {e}")
        return ["I was unable to retrieve your calendar, sir."]


# ── WEATHER ───────────────────────────────────────────────────────────────────
def get_weather_summary():
    """Returns a short spoken weather summary."""
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={LAT}&lon={LON}&appid={OPENWEATHER_API_KEY}&units=imperial"
        )
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data      = r.json()
            temp      = round(data["main"]["temp"])
            feels     = round(data["main"]["feels_like"])
            condition = data["weather"][0]["description"]
            humidity  = data["main"]["humidity"]
            return (
                f"Currently {temp} degrees Fahrenheit, feels like {feels}. "
                f"{condition.capitalize()}, with {humidity} percent humidity."
            )
    except Exception as e:
        print(f"[WEATHER ERROR] {e}")
    return "Weather data is unavailable at this time, sir."


# ── DAILY JOKE ────────────────────────────────────────────────────────────────
BACKUP_JOKES = [
    "Why don't scientists trust atoms? Because they make up everything.",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why did the scarecrow win an award? Because he was outstanding in his field.",
    "I'm reading a book about anti-gravity. It's impossible to put down.",
    "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I asked the library if they had books about paranoia. The librarian whispered, they're right behind you.",
]

def get_daily_joke():
    """Fetches a joke from an API with fallback to local jokes."""
    try:
        r = requests.get(
            "https://v2.jokeapi.dev/joke/Any?safe-mode&type=twopart",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("type") == "twopart":
                return f"{data['setup']} ... {data['delivery']}"
    except Exception as e:
        print(f"[JOKE ERROR] {e}")

    # Fallback: pick a joke based on the day of the week
    import datetime
    index = datetime.datetime.now().weekday() % len(BACKUP_JOKES)
    return BACKUP_JOKES[index]


# ── BEEP ALARM SOUND ──────────────────────────────────────────────────────────
def play_beeps(count=3, freq=880, duration=0.3, pause=0.2, sample_rate=44100):
    """Plays `count` beeps using sounddevice — no audio files needed."""
    t    = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    beep = (np.sin(2 * np.pi * freq * t) * 0.6).astype(np.float32)
    silence = np.zeros(int(sample_rate * pause), dtype=np.float32)
    for i in range(count):
        sd.play(beep, sample_rate)
        sd.wait()
        if i < count - 1:            sd.play(silence, sample_rate)
            sd.wait()


# ── MORNING BRIEFING ──────────────────────────────────────────────────────────
def deliver_briefing():
    now      = datetime.datetime.now()
    greeting = "Good morning" if now.hour < 12 else ("Good afternoon" if now.hour < 17 else "Good evening")
    date_str = now.strftime("%A, %B %d")

    voice_output.speak(f"{greeting}, sir. Today is {date_str}.")
    time.sleep(0.3)
    voice_output.speak("Here is your weather report.")
    voice_output.speak(get_weather_summary())
    time.sleep(0.3)
    voice_output.speak("Your schedule for today:")
    events = get_todays_events()
    for event in events:
        voice_output.speak(event)
        time.sleep(0.2)
    time.sleep(0.3)
    voice_output.speak("And finally, your daily joke, sir.")
    voice_output.speak(get_daily_joke())


# ── ALARM STORAGE ─────────────────────────────────────────────────────────────
def _load_alarms():
    if os.path.exists(ALARMS_FILE):
        try:
            with open(ALARMS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _save_alarms(alarms):
    with open(ALARMS_FILE, "w") as f:
        json.dump(alarms, f)


# ── ALARM PARSER ──────────────────────────────────────────────────────────────
def parse_alarm_time(command_text):
    """
    Extracts a time from spoken text.
    Handles: "7am", "7:30am", "7 30 am", "19:00", "half past 7"
    Returns a datetime for the next occurrence of that time, or None.
    """
    cmd = command_text.lower()

    # "half past X"
    half_past = re.search(r'half past (\d+)', cmd)
    if half_past:
        hour   = int(half_past.group(1))
        minute = 30
        period = "am" if hour < 12 else "pm"
        cmd    = f"{hour}:{minute}{period}"

    # Match time patterns
    match = re.search(
        r'(\d{1,2})(?:[:\s](\d{2}))?\s*(am|pm)?',
        cmd
    )
    if not match:
        return None

    hour   = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    period = match.group(3)

    if period == "pm" and hour != 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0

    now    = datetime.datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If time has already passed today, schedule for tomorrow
    if target <= now:
        target += datetime.timedelta(days=1)

    return target


# ── ALARM MANAGER ─────────────────────────────────────────────────────────────
class AlarmManager:
    def __init__(self):
        self.speak_fn  = None   # Set by brain.py after init
        self._thread   = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def set_speak(self, fn):
        self.speak_fn = fn

    def set_alarm(self, command_text):
        target = parse_alarm_time(command_text)
        if not target:
            return "I couldn't parse that time, sir. Please try again."
        alarms = _load_alarms()
        alarms.append(target.isoformat())
        _save_alarms(alarms)
        time_str = target.strftime("%I:%M %p").lstrip("0")
        return f"Alarm set for {time_str}, sir."

    def cancel_alarm(self):
        _save_alarms([])
        return "All alarms cancelled, sir."

    def list_alarms(self):
        alarms = _load_alarms()
        if not alarms:
            return "You have no alarms set, sir."
        times = []
        for a in alarms:
            dt = datetime.datetime.fromisoformat(a)
            times.append(dt.strftime("%I:%M %p").lstrip("0"))
        return "Your alarms are set for: " + ", ".join(times) + ", sir."

    def _loop(self):
        """Background thread — checks every 30 seconds if an alarm should fire."""
        while True:
            now    = datetime.datetime.now()
            alarms = _load_alarms()
            fired  = []
            remaining = []

            for a in alarms:
                target = datetime.datetime.fromisoformat(a)
                # Fire if within 30 seconds of target
                if abs((now - target).total_seconds()) <= 30:
                    fired.append(a)
                else:
                    remaining.append(a)

            if fired and self.speak_fn:
                _save_alarms(remaining)
                play_beeps(3)
                time.sleep(0.5)
                deliver_briefing()

            time.sleep(30)


# Singleton instance
alarm_manager = AlarmManager()


# ── COMMAND HANDLER (called by brain.py) ──────────────────────────────────────
def handle_alarm_command(command_text, speak_fn=None):
    """
    Routes alarm and briefing commands.
    Returns a (handled: bool, response: str) tuple.
    """
    if speak_fn:
        alarm_manager.set_speak(speak_fn)

    cmd = command_text.lower()

    # Set alarm
    if "set" in cmd and "alarm" in cmd:
        return True, alarm_manager.set_alarm(cmd)

    # Cancel alarm
    if ("cancel" in cmd or "delete" in cmd or "remove" in cmd) and "alarm" in cmd:
        return True, alarm_manager.cancel_alarm()

    # List alarms
    if ("what" in cmd or "list" in cmd or "when" in cmd) and "alarm" in cmd:
        return True, alarm_manager.list_alarms()

    # Manual briefing trigger
    if "morning briefing" in cmd or "briefing" in cmd or "daily briefing" in cmd:
        if speak.fn::
            threading.Thread(target=deliver_briefing, daemon=True).start()
            return True, ""   # briefing speaks for itself
        return True, "Speak function unavailable, sir."

    return False, ""
