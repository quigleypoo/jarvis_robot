import os
import requests
import json

# Load the advanced system prompt text file
PROMPT_FILE = "jarvis_prompt.txt"
if os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "r") as f:
        SYSTEM_PROMPT = f.read()
else:
    SYSTEM_PROMPT = "You are Jarvis, a helpful British AI assistant."

def process_command(user_speech):
    """Sends the speech to local Ollama with the Jarvis prompt, then splits text from robot actions."""
    url = "http://localhost:11434/api/generate"
    
    # Bundle the system prompt instructions together with what you said aloud
    full_prompt = f"System Instructions:\n{SYSTEM_PROMPT}\n\nUser Command: {user_speech}"
    
    payload = {
        "model": "llama3.2:1b",
        "prompt": full_prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload)
        response_data = json.loads(response.text)
        raw_ai_text = response_data.get("response", "").strip()
        
        # Check if Jarvis decided to trigger a physical robot arm command tag
        action_command = "CONVERSATION"
        if "[CMD:" in raw_ai_text:
            # Extract the exact tag (e.g., "[CMD:GRAB]")
            start_idx = raw_ai_text.find("[CMD:")
            end_idx = raw_ai_text.find("]", start_idx) + 1
            cmd_tag = raw_ai_text[start_idx:end_idx]
            
            # Clean up the action text for the Arduino logic
            action_command = cmd_tag.replace("[", "").replace("]", "")
            
            # Erase the tag from the text so Jarvis doesn't say "[CMD:GRAB]" out loud
            raw_ai_text = raw_ai_text.replace(cmd_tag, "").strip()
            
        return action_command, raw_ai_text

    except Exception as e:
        return "CONVERSATION", "I'm experiencing an internal processing error, sir. Ensure Ollama is running."
