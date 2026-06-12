import voice_input
import brain
import voice_output
import time
import serial

# Try to connect to your Arduino's USB slot
# Windows uses ports like 'COM3' or 'COM4'. Raspberry Pi uses '/dev/ttyUSB0'.
try:
    arduino = serial.Serial(port='COM3', baudrate=9600, timeout=1)
    print("🔌 Arduino connection successful on COM3!")
except Exception as e:
    arduino = None
    print("⚠️ Arduino not detected on laptop. Running in Local Virtual Mode.")

def start_jarvis():
    voice_output.speak("Systems fully loaded. I am online and listening, sir.")
    
    while True:
        speech_text = voice_input.listen_for_command()
        
        if speech_text:
            text_lower = speech_text.lower().strip()
            
            if "jarvis" in text_lower:
                print("🎯 Wake word 'Jarvis' detected!")
                clean_command = text_lower.replace("jarvis", "").strip()
                
                if not clean_command:
                    voice_output.speak("Yes, sir? I am standing by.")
                    continue
                
                print(f"🧠 Sending command to Jarvis Brain: '{clean_command}'")
                action, speech_response = brain.process_command(clean_command)
                
                # Speak out loud
                voice_output.speak(speech_response)
                
                # If the AI generated a mechanical movement command
                if action != "CONVERSATION":
                    print(f"⚙️ EXECUTING ARDUINO HARDWARE COMMAND -> {action}")
                    
                    # If an Arduino is physically plugged into USB, send the raw bytes down the wire
                    if arduino:
                        arduino.write(f"{action}\n".encode('utf-8'))
                    else:
                        print("🤖 [VIRTUAL SIMULATION]: Physical robotic arm would have moved now.")
                        
        time.sleep(0.5)

if __name__ == "__main__":
    start_jarvis()
