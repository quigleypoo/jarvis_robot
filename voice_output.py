import pyttsx3

def speak(text):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    # Try to find a male/British voice if available on your system
    for voice in voices:
        if "british" in voice.name.lower() or "male" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
            
    engine.setProperty('rate', 175) # Speed of speech
    print(f"Jarvis: {text}")
    engine.say(text)
    engine.runAndWait()
