import os
import json
import base64
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from ddgs import DDGS  

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

PROMPT_FILE = "jarvis_prompt.txt"
MEMORY_FILE = "jarvis_memory.json"

if os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
else:
    SYSTEM_PROMPT = "You are Jarvis, a helpful British AI assistant."

def load_conversation_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_conversation_memory(memory_history):
    trimmed_memory = memory_history[-6:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed_memory, f, indent=2)

def encode_image_to_base64(image_path):
    """Converts a local physical image file into a text string for the cloud API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def search_the_web(query: str) -> str:
    """Browses the live internet to get real-time facts, weather, news, or item prices."""
    try:
        print(f"🌐 [JARVIS LIVE SEARCHING THE WEB FOR: '{query}']")
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=2)]
            if results:
                return "\n".join([f"Source: {r['title']} - {r['body']}" for r in results])
    except Exception as e:
        return f"Search link error: {str(e)}"
    return "No live data found, sir."

def process_command(user_speech):
    """Routes voice queries cleanly by isolating tools from the conversational text loop."""
    if not client:
        return "CONVERSATION", "My cloud core interface link is offline, sir."
        
    command_clean = user_speech.lower().strip()
    past_exchanges = load_conversation_memory()
    
    # ─── ROUTE 1: HARDWARE CAMERA LIVE REFRESH WINDOW ───
    if any(k in command_clean for k in ["open camera", "activate lenses", "turn on video", "open cameras"]):
        print("🤖 [JARVIS IS INITIALIZING OPTICAL CHANNELS]")
        import vision
        vision.activate_camera()  
        return "CONVERSATION", "Optical array initialization complete. Lenses are broadcasting, sir."

    # ─── ROUTE 2: MULTIMODAL SIGHT SNAPSHOT SCAN ───
    if any(k in command_clean for k in ["scan", "identify", "what is this", "look at"]):
        print("🤖 [JARVIS TRIGGERING MULTIMODAL SIGHT SENSORS]")
        import vision
        image_name = "target_sight.jpg"
        if vision.snapshot_item(image_name):
            base64_image = encode_image_to_base64(image_name)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(past_exchanges)
            messages.append({"role": "user", "content": [
                {"type": "text", "text": f"Analyze this image and answer my question: {user_speech}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]})
            try:
                # FIX: Upgraded to Groq's official high-performance Llama 4 Vision engine
                response = client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct", 
                    messages=messages,
                    max_tokens=120
                )
                if os.path.exists(image_name):
                    os.remove(image_name)
                ai_reply = response.choices[0].message.content
                past_exchanges.append({"role": "user", "content": user_speech})
                past_exchanges.append({"role": "assistant", "content": ai_reply})
                save_conversation_memory(past_exchanges)
                return "CONVERSATION", ai_reply
            except Exception as e:
                if os.path.exists(image_name):
                    os.remove(image_name)
                print(f"⚠️ INTERNAL VISION ERROR CODE: {e}")
                return "CONVERSATION", "I'm having trouble compiling the image telemetry, sir."

    # ─── ROUTE 3: ISOLATED HARDWARE CLOCK TOOL ───
    if any(k in command_clean for k in ["time", "what time", "current date", "day is it"]):
        print("🤖 [JARVIS READING PHYSICAL SYSTEM CLOCK ARRAY]")
        real_time = datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")
        user_speech = f"{user_speech} (Context Notes: The hardware motherboard clock reads exactly: {real_time})"

    # ─── ROUTE 4: ISOLATED LIVE DUCKDUCKGO WEB BROWSER ───
    if any(k in command_clean for k in ["weather", "price of", "stock price", "news about", "tomorrow's forecast"]):
        web_facts = search_the_web(command_clean)
        user_speech = f"{user_speech} (Context Notes: Live internet query data snippets gathered for you:\n{web_facts})"

    # ─── ROUTE 5: STANDARD CHAT PIPELINE ───
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(past_exchanges)
    messages.append({"role": "user", "content": user_speech})
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=120
        )
        ai_reply = response.choices[0].message.content
        
        past_exchanges.append({"role": "user", "content": user_speech.split("(Context Notes:")[0].strip()})
        past_exchanges.append({"role": "assistant", "content": ai_reply})
        save_conversation_memory(past_exchanges)
        
        return "CONVERSATION", ai_reply

    except Exception as e:
        print(f"⚠️ Core Execution Error: {e}")
        return "CONVERSATION", "Transmission lag is interrupting my dialogue loops, sir."
