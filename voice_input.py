import sys
import queue
import json

# ─── AUDIO CAPTURE AND SPEECH ENGINE REGISTRATION ───
try:
    import sounddevice as sd
    from vosk import Model, KaldiRecognizer
    HAS_VOICE_HARDWARE = True
except ImportError:
    HAS_VOICE_HARDWARE = False

class VoiceManager:
    def __init__(self, model_path="model"):
        self.audio_queue = queue.Queue()
        self.initialized = False
        
        if HAS_VOICE_HARDWARE:
            try:
                # Attempts to load local offline model files to avoid internet dependency
                self.model = Model(model_path)
                self.recognizer = KaldiRecognizer(self.model, 16000)
                self.initialized = True
                print("[AUDIO] Vosk core and USB microphone initialized successfully.")
            except Exception as e:
                print(f"[AUDIO WARN] Voice components found, but failed to load model folder: {e}")
                print("Defaulting back to local testing interface...")

    def audio_callback(self, indata, frames, time, status):
        """Asynchronously pipes chunks of audio data straight into our queue."""
        if status:
            print(status, file=sys.stderr)
        self.audio_queue.put(bytes(indata))

    def listen_stream(self):
        """Streams real-time microphone audio and parses speech strings instantly."""
        print("\n🎙️ [JARVIS IS ACTIVE AND LISTENING VIA AUDIO CHANNELS]...")
        
        # Starts a fast raw input audio channel at a clean 16kHz frequency
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                               channels=1, callback=self.audio_callback):
            while True:
                data = self.audio_queue.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text_out = result.get("text", "").strip()
                    if text_out:
                        return text_out

# Instantiate our voice tracking engine
_manager = VoiceManager(model_path="model")

def listen_for_command():
    """
    Main gateway used by main.py. Automatically switches from typing-simulation
    to fully functional voice capture if hardware libraries are present.
    """
    if HAS_VOICE_HARDWARE and _manager.initialized:
        try:
            return _manager.listen_stream()
        except Exception as e:
            print(f"⚠️ Microphone feed interrupted: {e}. Launching keyboard typing recovery...")
    
    # ─── LAPTOP KEYBOARD SIMULATOR BACKUP ───
    print("\n⌨️ LAPTOP SIMULATOR MODE")
    print("Type what you want to say to Jarvis (include the word 'Jarvis')")
    user_typed_text = input("Speak: ")
    return user_typed_text
