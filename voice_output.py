import os
import sounddevice as sd

# Safely connect to our local Kokoro ONNX execution engine
try:
    from kokoro_onnx import KokoroOnnx
    # Updated file path to look for the correct 'voices.bin' filename asset
    if os.path.exists("kokoro-v0_19.onnx") and os.path.exists("voices.bin"):
        kokoro = KokoroOnnx("kokoro-v0_19.onnx", "voices.bin")
    else:
        kokoro = None
        print("⚠️ Kokoro file assets are missing from the folder directory.")
except Exception as err:
    kokoro = None
    print(f"⚠️ NEURAL AUDIO LOAD ERROR: {err}")

def speak(text):
    """Generates a highly realistic local British cinematic voice completely for free."""
    print(f"Jarvis: {text}")
    
    if kokoro:
        try:
            # We command Kokoro to generate audio using the 'en_GB-alan' British profile
            # speed=0.88 slows him down by 12% to match Paul Bettany's cinematic cadence
            samples, sample_rate = kokoro.create(
                text, 
                voice="en_GB-alan", 
                speed=0.88
            )
            
            # Stream the generated audio arrays straight over your speakers
            sd.play(samples, sample_rate)
            sd.wait()  # Hold the script loop until Jarvis finishes speaking his sentence
            return
        except Exception as e:
            print(f"⚠️ Kokoro generation stuttered: {e}. Dropping back to system default.")

    # Fallback Protection: Keeps your workspace running if files are misplaced
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass
