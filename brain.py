import os
import base64
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

PROMPT_FILE = "jarvis_prompt.txt"
if os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
else:
    SYSTEM_PROMPT = "You are Jarvis, a helpful British AI assistant."

def encode_image_to_base64(image_path):
    """Converts a local physical image file into a text string for the cloud API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_command(user_speech):
    """Routes voice queries. Triggers a visual scan if the user asks Jarvis to look at something."""
    if not client:
        return "CONVERSATION", "My cloud core interface link is offline, sir."
        
    command_clean = user_speech.lower().strip()
    
    # ─── DETECT VISUAL ANALYSIS REQUESTS ───
    if any(keyword in command_clean for keyword in ["scan", "identify", "what is this", "look at"]):
        print("🤖 [JARVIS TRIGGERING MULTIMODAL SIGHT SENSORS]")
        import vision
        
        # Snap the picture using the system's hardware camera
        image_name = "target_sight.jpg"
        if vision.snapshot_item(image_name):
            # Encode the picture matrix
            base64_image = encode_image_to_base64(image_name)
            
            # Construct a Vision Prompt payload
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": f"Analyze this image and answer my question: {user_speech}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ]
            
            try:
                # Ship the text AND the image over the network using the Vision Model
                response = client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview", # Specialized local-cloud vision AI
                    messages=messages,
                    max_tokens=100
                )
                
                # Delete the temp file to keep your workspace pristine
                if os.path.exists(image_name):
                    os.remove(image_name)
                    
                return "CONVERSATION", response.choices[0].message.content
            except Exception as e:
                if os.path.exists(image_name):
                    os.remove(image_name)
                print(f"⚠️ Vision Link Error: {e}")
                return "CONVERSATION", "I'm having trouble compiling the image telemetry, sir."
                
    # ─── DEFAULT CONVERSATIONAL MODE ───
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_speech}
    ]
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=100
        )
        return "CONVERSATION", response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Conversation Link Error: {e}")
        return "CONVERSATION", "Transmission lag is interrupting my dialogue loops, sir."
