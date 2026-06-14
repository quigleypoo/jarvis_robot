import os
import numpy as np
import sounddevice as sd

# ─── NEURAL SYNTHESIS SYSTEM ARCHITECTURE ───
try:
    from kokoro_onnx import KokoroOnnx
    # Validates that your offline weight matrix files are stored in the project directory
    if os.path.exists("kokoro-v0_19.onnx") and os.path.exists("voices.bin"):
        kokoro = KokoroOnnx("kokoro-v0_19.onnx", "voices.bin")
    else:
        kokoro = None
        print("⚠️ Kokoro weight assets are missing from the current folder directory.")
except Exception as err:
    kokoro = None
    print(f"⚠️ NEURAL AUDIO LOAD ERROR: {err}")

def speak(text):
    """Generates an offline British voice using Kokoro, with automatic fallback structures."""
    print(f"Jarvis: {text}")
    
    if kokoro:
        try:
            # Generate local synthetic audio arrays using the Alan British voice profile
            samples, sample_rate = kokoro.create(
                text, 
                voice="en_GB-alan", 
                speed=0.88
            )
            
            # HARDWARE FIX: Ensure numpy float32 conversion before pushing data to your USB speakers
            samples = np.array(samples, dtype=np.float32)
            
            # Prevent audio stream collision by cleanly stopping any leftover audio processes
            sd.stop() 
            
            # Stream the processed neural data blocks smoothly
            sd.play(samples, sample_rate)
            sd.wait()  # Hold the script loop until Jarvis finishes speaking his sentence
            return
        except Exception as e:
            print(f"⚠️ Kokoro generation stuttered: {e}. Dropping back to system default.")

    # FALLBACK PROTECTION: Keeps your workspace running if files are misplaced
    try:
        import pyttsx3
        engine = pyttsx3.init()
        # Find a local British system voice if available
        voices = engine.getProperty('voices')
        for v in voices:
            if "GB" in v.id or "british" in v.name.lower():
                engine.setProperty('voice', v.id)
                break
        engine.setProperty('rate', 160)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        # Final emergency safeguard: print statements continue even if audio systems drop entirely
        pass
