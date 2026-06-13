import os
import json
import base64
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from duckduckgo_search import DDGS  

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
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_current_system_time():
    """Returns the precise local system date and time from the motherboard clock."""
    return datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")

def search_the_web(query: str) -> str:
    """Browses the live internet to get real-time facts, weather, news, or item prices."""
    try:
        print(f"🌐 [JARVIS LIVE SEARCHING THE WEB FOR: '{query}']")
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if results:
                return "\n".join([f"Source: {r['title']} - {r['body']}" for r in results])
    except Exception as e:
        return f"Internet search link error: {str(e)}"
    return "No live data found on the web for this query, sir."

def process_command(user_speech):
    """Processes queries, checking if the cloud needs to search the web or read the hardware clock."""
    if not client:
        return "CONVERSATION", "My cloud core interface link is offline, sir."
        
    command_clean = user_speech.lower().strip()
    past_exchanges = load_conversation_memory()
    
    # ─── CAMERA PROTOCOLS ───
    if any(keyword in command_clean for keyword in ["scan", "identify", "what is this", "look at"]):
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
                response = client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview",
                    messages=messages,
                    max_tokens=100
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
                return "CONVERSATION", "I'm having trouble compiling the image telemetry, sir."
                
    # ─── CORE CHAT WITH DUAL HARDWARE & WEB TOOLS ───
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(past_exchanges)
    messages.append({"role": "user", "content": user_speech})
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_system_time",
                "description": "Call this whenever the user asks for the current time, date, day, or temporal context.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_the_web",
                "description": "Call this whenever the user asks about live prices, weather forecasts, news, or any real-time data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The target search query keywords to browse on the web."}
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=100
        )
        
        # FIX 1: Re-added the missing index bracket tracker right here
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                t_name = tool_call.function.name
                
                if t_name == "get_current_system_time":
                    print("🤖 [JARVIS READING PHYSICAL SYSTEM CLOCK ARRAY]")
                    tool_result = get_current_system_time()
                elif t_name == "search_the_web":
                    t_args = json.loads(tool_call.function.arguments)
                    search_query = t_args.get("query")
                    tool_result = search_the_web(search_query)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": t_name,
                    "content": tool_result
                })
            
            final_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=100
            )
            # FIX 2: Added the index bracket to the secondary response call too
            ai_reply = final_response.choices[0].message.content
            past_exchanges.append({"role": "user", "content": user_speech})
            past_exchanges.append({"role": "assistant", "content": ai_reply})
            save_conversation_memory(past_exchanges)
            return "CONVERSATION", ai_reply
                    
        ai_reply = response_message.content
        past_exchanges.append({"role": "user", "content": user_speech})
        past_exchanges.append({"role": "assistant", "content": ai_reply})
        save_conversation_memory(past_exchanges)
        return "CONVERSATION", ai_reply

    except Exception as e:
        print(f"⚠️ Core Execution Error: {e}")
        return "CONVERSATION", "Transmission lag is interrupting my dialogue loops, sir."
