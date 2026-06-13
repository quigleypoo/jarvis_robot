import os
import json
import base64
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

PROMPT_FILE = "jarvis_prompt.txt"
MEMORY_FILE = "jarvis_memory.json"

# Load your custom system prompt behavior metrics
if os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
else:
    SYSTEM_PROMPT = "You are Jarvis, a helpful British AI assistant."

def load_conversation_memory():
    """Loads past contextual memories from a fast local JSON array layer."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_conversation_memory(memory_history):
    """Saves the rolling context history snippet, capping it to the last 6 entries to prevent lag."""
    # Keep only the last 6 messages (3 back-and-forth exchanges) to guarantee zero latency growth
    trimmed_memory = memory_history[-6:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed_memory, f, indent=2)

def encode_image_to_base64(image_path):
    """Converts a local physical image file into a text string for the cloud API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_command(user_speech):
    """Routes voice queries with instant sliding-window conversational memory tracking."""
    if not client:
        return "CONVERSATION", "My cloud core interface link is offline, sir."
        
    command_clean = user_speech.lower().strip()
    past_exchanges = load_conversation_memory()
    
    # ─── SCENARIO A: DETECT VISUAL ANALYSIS REQUESTS ───
    if any(keyword in command_clean for keyword in ["scan", "identify", "what is this", "look at"]):
        print("🤖 [JARVIS TRIGGERING MULTIMODAL SIGHT SENSORS]")
        import vision
        
        image_name = "target_sight.jpg"
        if vision.snapshot_item(image_name):
            base64_image = encode_image_to_base64(image_name)
            
            # Reconstruct payload including our system prompt and past conversation history
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(past_exchanges)
            messages.append({"role": "user", "content": [
                {"type": "text", "text": f"Analyze this image and answer my question: {user_speech}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]})
            
            try:
                response = client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview",
                    messages=messages,
                    max_tokens=100
                )
                if os.path.exists(image_name):
                    os.remove(image_name)
                
                ai_reply = response.choices[0].message.content
                # Save this exchange to our memory logs
                past_exchanges.append({"role": "user", "content": user_speech})
                past_exchanges.append({"role": "assistant", "content": ai_reply})
                save_conversation_memory(past_exchanges)
                
                return "CONVERSATION", ai_reply
            except Exception as e:
                if os.path.exists(image_name):
                    os.remove(image_name)
                print(f"⚠️ Vision Link Error: {e}")
                return "CONVERSATION", "I'm having trouble compiling the image telemetry, sir."
                
    # ─── SCENARIO B: DEFAULT CONVERSATIONAL MODE WITH MEMORY ───
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Inject whatever you guys talked about earlier in the session seamlessly
    messages.extend(past_exchanges)
    messages.append({"role": "user", "content": user_speech})
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=100
        )
        ai_reply = response.choices[0].message.content
        
        # Append the fresh dialogue loop directly to our rolling memory
        past_exchanges.append({"role": "user", "content": user_speech})
        past_exchanges.append({"role": "assistant", "content": ai_reply})
        save_conversation_memory(past_exchanges)
        
        return "CONVERSATION", ai_reply
    except Exception as e:
        print(f"⚠️ Conversation Link Error: {e}")
        return "CONVERSATION", "Transmission lag is interrupting my dialogue loops, sir."
