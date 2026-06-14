import serial
import speech_recognition as sr
import pyttsx3
import requests
import json
import threading
import time

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB0'  # Adjust to your Pi's USB port (e.g., /dev/ttyACM0)
BAUD_RATE = 115200
OLLAMA_URL = "http://localhost:11434/api/generate"  # Local AI server endpoint

# --- INITIALIZE AUDIO ENGINE ---
tts_engine = pyttsx3.init()
# Set Jarvis voice properties (Adjust speed and volume)
tts_engine.setProperty('rate', 145) 
tts_engine.setProperty('volume', 1.0)

# Global variables for cross-thread data sharing
latest_glove_data = {}

def jarvis_speak(text):
    """Makes the Raspberry Pi speak out loud."""
    print(f"Jarvis: {text}")
    tts_engine.say(text)
    tts_engine.runAndWait()

# --- STEP 1: GLOVE TELEMETRY PARSER (RUNS IN BACKGROUND) ---
def parse_glove_stream():
    """Background thread to read and parse the ESP32 data stream."""
    global latest_glove_data
    print(f"Connecting to smart glove on {SERIAL_PORT}...")
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        ser.flush()
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                
                # Expected stream format: Thumb,Index,Middle,Ring,Pinky|ax,ay,az|gx,gy,gz
                if '|' in line:
                    try:
                        parts = line.split('|')
                        fingers = [int(x) for x in parts[0].split(',')]
                        accel = [int(x) for x in parts[1].split(',')]
                        gyro = [int(x) for x in parts[2].split(',')]
                        
                        latest_glove_data = {
                            "fingers": fingers,
                            "accel": accel,
                            "gyro": gyro,
                            "gesture": detect_gesture(fingers, accel)
                        }
                    except (ValueError, IndexError):
                        continue # Skip corrupted lines smoothly
            time.sleep(0.01)
    except Exception as e:
        print(f"Glove connection offline: {e}")

def detect_gesture(fingers, accel):
    """Translates raw sensor telemetry into high-level gestures."""
    # Example heuristic baseline: low analog numbers = fully bent
    is_fist = all(f < 1500 for f in fingers)
    is_flat = all(f > 3000 for f in fingers)
    
    if is_fist: return "CLOSED_FIST"
    if is_flat: return "OPEN_PALM"
    return "UNKNOWN"

# --- STEP 2: LOCAL AI AI BRAIN PROCESSING ---
def ask_jarvis_ai(prompt):
    """Sends voice input and glove state to a local AI instance."""
    g_state = latest_glove_data.get("gesture", "UNKNOWN")
    f_state = latest_glove_data.get("fingers", [0,0,0,0,0])
    
    # Inject spatial awareness into Jarvis context
    system_context = (
        f"You are Jarvis, an advanced AI system. You are tracking the user's robotic arm glove. "
        f"Current hand posture: {g_state}. Finger raw telemetry values: {f_state}. "
        f"Keep responses ultra-short, technical, and helpful. Be concise like the movie character."
    )
    
    payload = {
        "model": "llama3", # Change to "mistral" or your local model
        "prompt": f"{system_context}\nUser: {prompt}\nJarvis:",
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json().get("response", "System error processing response.")
    except Exception:
        return "Connection to my core cognitive mainframe failed, sir."

# --- STEP 3: CONTINUOUS VOICE LISTENER LOOP ---
def main_voice_loop():
    """Listens for speech and routes commands."""
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
    jarvis_speak("Online and operational, sir. Glove tracking initialized.")
    
    while True:
        try:
            with microphone as source:
                print("\nListening...")
                audio = recognizer.listen(source, phrase_time_limit=5)
                
            print("Processing speech...")
            user_input = recognizer.recognize_google(audio).lower()
            print(f"You said: {user_input}")
            
            # Simple keyword intercept or full AI pass-through
            if "jarvis" in user_input:
                clean_prompt = user_input.replace("jarvis", "").strip()
                
                # Let Jarvis know if you're trying to execute an arm command via hand stance
                if "arm" in clean_prompt or "hand" in clean_prompt:
                    current_posture = latest_glove_data.get("gesture", "UNKNOWN")
                    jarvis_speak(f"Current hand alignment is {current_posture}. Proceeding with system verification.")
                else:
                    # Query the local language model
                    ai_reply = ask_jarvis_ai(clean_prompt)
                    jarvis_speak(ai_reply)
                    
        except sr.UnknownValueError:
            pass # Ignore unreadable room noise silently
        except sr.RequestError:
            print("Voice recognition API connectivity issue.")

# --- START CENTRAL BRAIN RUNTIME ---
if __name__ == "__main__":
    # Launch glove tracking thread so it does not block voice listening
    glove_thread = threading.Thread(target=parse_glove_stream, daemon=True)
    glove_thread.start()
    
    # Run the main Jarvis interface
    main_voice_loop()
