import os
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage

# TOOL 1: File Reading capability (Ruggedized with UTF-8)
@tool
def read_project_file(filename: str = "jarvis_prompt.txt") -> str:
    """Reads the contents of a local project script file (e.g., 'brain.py', 'main.py')."""
    clean_name = os.path.basename(str(filename))
    if os.path.exists(clean_name):
        # FIX: Added encoding="utf-8" to safely read files containing emojis
        with open(clean_name, "r", encoding="utf-8") as f:
            return f.read()
    return f"Error: File '{clean_name}' not found."

# TOOL 2: Self-Modification file writing capability (Ruggedized with UTF-8)
@tool
def modify_project_file(filename: str, new_code_content: str) -> str:
    """Completely overwrites a local project script file with new, updated python code."""
    clean_name = os.path.basename(str(filename))
    test_filename = f"test_{clean_name}"
    try:
        with open(test_filename, "w", encoding="utf-8") as f:
            f.write(new_code_content)
        compile(new_code_content, test_filename, 'exec')
        with open(clean_name, "w", encoding="utf-8") as f:
            f.write(new_code_content)
        if os.path.exists(test_filename):
            os.remove(test_filename)
        return f"Success: '{clean_name}' has been successfully updated and saved."
    except Exception as e:
        if os.path.exists(test_filename):
            os.remove(test_filename)
        return f"Refused to save: The generated code contains a syntax error: {str(e)}"

# TOOL 3: Vision Engine Integration
@tool
def trigger_camera_protocol() -> str:
    """Activates Jarvis's webcam or Pi Camera Module 3 optical sensors for real-time tracking."""
    import vision
    vision.activate_camera()
    return "Optical array initialization complete. Feeds are actively rendering, sir."


# Bind all three tools to our local Llama model
llm = ChatOllama(model="llama3.2:1b", temperature=0.1).bind_tools([
    read_project_file, 
    modify_project_file, 
    trigger_camera_protocol
])

PROMPT_FILE = "jarvis_prompt.txt"
if os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
else:
    SYSTEM_PROMPT = "You are Jarvis, a helpful British AI assistant."

def process_command(user_speech):
    """Processes commands and formats data securely using LangChain .invoke method."""
    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", user_speech)
    ]
    
    try:
        # First query to the local LLM
        response = llm.invoke(messages)
        
        # If Jarvis decides he needs to execute an instruction tool block
        if response.tool_calls:
            messages.append(response)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                print(f"🤖 [JARVIS IS ACCESSING INTERNAL SYSTEM MATRIX: {tool_name}]")
                
                result = ""
                if tool_name == "read_project_file":
                    target_file = tool_args.get("filename", "jarvis_prompt.txt")
                    result = read_project_file.invoke({"filename": target_file})
                elif tool_name == "modify_project_file":
                    target_file = tool_args.get("filename")
                    new_code = tool_args.get("new_code_content")
                    if target_file and new_code:
                        result = modify_project_file.invoke({"filename": target_file, "new_code_content": new_code})
                    else:
                        result = "Error: Missing filename or content parameter arrays."
                elif tool_name == "trigger_camera_protocol":
                    result = trigger_camera_protocol.invoke({})
                
                # Explicitly bundle the execution result as a structural ToolMessage
                messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
            
            # Send the completed history back to Ollama to summarize out loud
            final_response = llm.invoke(messages)
            return "CONVERSATION", final_response.content
                
        return "CONVERSATION", response.content

    except Exception as e:
        print(f"⚠️ Debug Core Exception: {e}") 
        return "CONVERSATION", "I'm having difficulty adjusting my own system modules, sir."
