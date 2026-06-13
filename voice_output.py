import os
import wave
import numpy as np

try:
    from piper import PiperVoice
except ImportError:
    PiperVoice = None

def speak(text):
    """Directly runs the downloaded ONNX model via the native Python Piper library."""
    print(f"Jarvis: {text}")
    
    model_path = "en_GB-jarvis-medium.onnx"
    output_wav = "jarvis_response.wav"
    
    if PiperVoice and os.path.exists(model_path):
        try:
            voice = PiperVoice.load(model_path)
            
            with wave.open(output_wav, "wb") as wav_file:
                voice.synthesize(text, wav_file, length_scale=1.15, noise_scale=0.7)
            
            if os.name == 'nt':
                import winsound
                winsound.PlaySound(output_wav, winsound.SND_FILENAME)
            else:
                os.system(f"aplay {output_wav}")
                
            if os.path.exists(output_wav):
                os.remove(output_wav)
            return
            
        except Exception as e:
            print(f"⚠️ Native Piper processing failed: {e}. Falling back to default narrator.")

    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for voice in voices:
            if "british" in voice.name.lower() or "male" in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        engine.setProperty('rate', 165)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass
