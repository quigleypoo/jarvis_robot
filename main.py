import voice_input
import brain
import voice_output
import time

def start_jarvis():
    # Track whether Jarvis is currently awake or asleep
    is_awake = False
    
    # Track the exact timestamp of when you last spoke to him
    last_interaction_time = 0
    
    # UPDATED: The listening window is now set to 30.0 seconds
    TIMEOUT_LIMIT = 30.0
    
    voice_output.speak("Systems fully loaded. I am online and listening, sir.")
    
    while True:
        speech_text = voice_input.listen_for_command()
        current_time = time.time()
        
        if speech_text:
            text_lower = speech_text.lower().strip()
            
            # SCENARIO 1: Jarvis is asleep, and you say his name to wake him up
            if not is_awake and "jarvis" in text_lower:
                print("🎯 Wake word 'Jarvis' detected! Initializing session...")
                is_awake = True
                last_interaction_time = current_time
                
                # Clean up his name and see if you said a command right away
                clean_command = text_lower.replace("jarvis", "").strip()
                
                if not clean_command:
                    voice_output.speak("Yes, sir? I am standing by.")
                    continue
                    
            # SCENARIO 2: Jarvis is already awake, so we process whatever you say immediately
            elif is_awake:
                print("💬 Session Active: Processing open voice stream...")
                last_interaction_time = current_time # Reset the timer because you are talking
                clean_command = text_lower
                
            # SCENARIO 3: Jarvis is asleep, and you didn't say his name (Ignore it)
            else:
                continue
                
            # --- THE CORE AI PROCESSING BLOCK ---
            print(f"🧠 Sending command to Jarvis Brain: '{clean_command}'")
            action, speech_response = brain.process_command(clean_command)
            
            # Speak out loud
            voice_output.speak(speech_response)
            
            # Log any structural physical robotic movements
            if action != "CONVERSATION":
                print(f"⚙️ EXECUTING ARDUINO HARDWARE COMMAND -> {action}")
                
        # --- THE CONVERSATIONAL TIMEOUT ENGINE ---
        # If Jarvis is awake, check if the 30-second countdown has run out
        if is_awake and (current_time - last_interaction_time > TIMEOUT_LIMIT):
            print("💤 Session Timeout: Putting Jarvis back into standby sleep mode.")
            voice_output.speak("Standing by, sir.")
            is_awake = False
            
        time.sleep(0.1)

if __name__ == "__main__":
    start_jarvis()
