"""
brain.py — Jarvis core, with HUD integration and process_command wrapper.
"""
import os
import serial
import speech_recognition as sr
import requests
import json
from groq import Groq
import threading
import time
import subprocess
import sys
import voice_output
import spotify_control as spotify_handler
import computer_control
import alarm_briefing

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
print(f"DEBUG KEY: {os.getenv('GROQ_API_KEY')}")
from hud_state    import write_state
from hud_services import start_hud_services

# --- CONFIGURATION ---
SERIAL_PORT  = '/dev/ttyUSB0'
BAUD_RATE    = 115200
import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = "llama-3.1-8b-instant"
groq_client  = Groq(api_key=GROQ_API_KEY)

latest_glove_data = {}


# --- SPEAK ---
def jarvis_speak(text, whisper=False):
    print(f"Jarvis: {text}")
    state = "whispering" if whisper else "speaking"
    write_state({"jarvis_state": state})
    voice_output.speak(text)
    write_state({"jarvis_state": "idle"})


# --- STEP 1: GLOVE TELEMETRY PARSER ---
def parse_glove_stream():
    global latest_glove_data
    print(f"Connecting to smart glove on {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        ser.flush()
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if '|' in line:
                    try:
                        parts   = line.split('|')
                        fingers = [int(x) for x in parts[0].split(',')]
                        accel   = [int(x) for x in parts[1].split(',')]
                        gyro    = [int(x) for x in parts[2].split(',')]
                        latest_glove_data = {
                            "fingers": fingers,
                            "accel":   accel,
                            "gyro":    gyro,
                            "gesture": detect_gesture(fingers, accel)
                        }
                    except (ValueError, IndexError):
                        continue
            time.sleep(0.01)
    except Exception as e:
        print(f"Glove connection offline: {e}")


def detect_gesture(fingers, accel):
    is_fist = all(f < 1500 for f in fingers)
    is_flat = all(f > 3000 for f in fingers)
    if is_fist: return "CLOSED_FIST"
    if is_flat: return "OPEN_PALM"
    return "UNKNOWN"


# --- STEP 2: AI BRAIN ---
def ask_jarvis_ai(prompt):
    g_state = latest_glove_data.get("gesture", "UNKNOWN")
    f_state = latest_glove_data.get("fingers", [0, 0, 0, 0, 0])

    try:
        with open("jarvis_prompt.txt", "r") as f:
            personality = f.read().strip()
    except FileNotFoundError:
        personality = "You are Jarvis, Tony Stark's AI assistant. Be brief and call the user sir."

    system_context = (
        f"{personality}\n\n"
        f"Context Notes: Current hand posture is {g_state}. Finger telemetry: {f_state}."
    )

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_context},
                {"role": "user",   "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return "Connection to my core cognitive mainframe failed, sir."


# --- STEP 3: PROCESS COMMAND (called by main.py) ---
def process_command(text):
    """
    Entry point expected by main.py.
    Returns an (action, speech_response) tuple.

    Actions:
      "ARM_COMMAND"   — physical arm/glove movement
      "MUSIC_COMMAND" — Spotify control
      "CONVERSATION"  — standard AI reply
    """
    write_state({"jarvis_state": "thinking"})
    text = text.lower().strip()

    # --- ARM / GLOVE COMMANDS ---
    arm_keywords = ["arm", "grip", "fist", "open", "close", "move", "rotate", "grab", "release"]
    if any(word in text for word in arm_keywords):
        gesture  = latest_glove_data.get("gesture", "UNKNOWN")
        fingers  = latest_glove_data.get("fingers", [0, 0, 0, 0, 0])
        response = (
            f"Current hand alignment is {gesture}. "
            f"Finger telemetry reads {fingers}. Executing motor sequence."
        )
        write_state({"jarvis_state": "idle"})
        return ("ARM_COMMAND", response)

    # --- MUSIC COMMANDS ---
    music_keywords = ["play", "pause", "resume", "skip", "next song", "stop the music"]
    if any(word in text for word in music_keywords):
        response = spotify_handler.handle_music_command(text)
        write_state({"jarvis_state": "idle"})
        return ("MUSIC_COMMAND", response)

# --- ALARM & BRIEFING COMMANDS ---
    alarm_keywords = ["alarm", "briefing", "wake me"]
    if any(word in text for word in alarm_keywords):
        handled, response = alarm_briefing.handle_alarm_command(text, speak_fn=jarvis_speak)
        if handled:
            write_state({"jarvis_state": "idle"})
            if response:
                return ("ALARM_COMMAND", response)

# --- COMPUTER CONTROL COMMANDS ---
    computer_keywords = ["open", "launch", "screenshot", "volume", "mute",
                         "search for", "search", "look up", "google", "louder",
                         "quieter", "find me", "show me"]
    if any(word in text for word in computer_keywords):
        result = computer_control.handle_computer_command(text)
        if result:
            write_state({"jarvis_state": "idle"})
            return ("COMPUTER_COMMAND", result)

    # --- EVERYTHING ELSE → AI ---
    response = ask_jarvis_ai(text)
    write_state({"jarvis_state": "idle"})
    return ("CONVERSATION", response)


# --- STEP 4: STANDALONE VOICE LOOP (used if you run brain.py directly) ---
def main_voice_loop():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    jarvis_speak("Online and operational, sir. Glove tracking initialized.")

    while True:
        try:
            write_state({"jarvis_state": "listening"})

            with microphone as source:
                print("\nListening...")
                audio = recognizer.listen(source, phrase_time_limit=5)

            write_state({"jarvis_state": "thinking"})
            print("Processing speech...")
            user_input = recognizer.recognize_google(audio).lower()
            print(f"You said: {user_input}")

            if "jarvis" in user_input:
                clean_prompt = user_input.replace("jarvis", "").strip()
                action, reply = process_command(clean_prompt)
                jarvis_speak(reply)
            else:
                write_state({"jarvis_state": "idle"})

        except sr.UnknownValueError:
            write_state({"jarvis_state": "idle"})
        except sr.RequestError:
            print("Voice recognition API connectivity issue.")


# --- MAIN RUNTIME (only runs if you launch brain.py directly) ---
if __name__ == "__main__":
    hud_proc = subprocess.Popen(
        [sys.executable, "hud_display.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    start_hud_services()

    glove_thread = threading.Thread(target=parse_glove_stream, daemon=True)
    glove_thread.start()

    try:
        main_voice_loop()
    finally:
        hud_proc.terminate()
