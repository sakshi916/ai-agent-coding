import ollama
from pathlib import Path
from read_tools import TOOLS as READ_TOOLS, DISPATCH as READ_DISPATCH
from session_management import load_session, save_session
from model import MODEL
from write_tools  import TOOLS as WRITE_TOOLS,  DISPATCH as WRITE_DISPATCH
from command_registry import handle_command

# Build merged registries
TOOLS    = READ_TOOLS + WRITE_TOOLS
DISPATCH = {**READ_DISPATCH, **WRITE_DISPATCH}

def run(user_msg, history, system_prompt):
    history.append({"role":"user","content":user_msg})
    msgs = [
        {"role":"system","content":
         f"You are a local coding assistant. Working in this workspace:{Path.cwd()}.\n" + system_prompt},
        *history[-40:]                      # keep last 40 messages in context
    ]
    for _ in range(8):
        resp = ollama.chat(model=MODEL, messages=msgs, tools=TOOLS)
        m = resp["message"]
        #print("------------message------------", m)
        '''
        role='assistant' content='' thinking='The user wants to list files in their folder. The folder is "llm-playground". I\'ll list the contents of that directory.' images=None tool_name=None tool_calls=[ToolCall(function=Function(name='list_folder', arguments={'path': 'llm-playground'}))]
        '''
        if m.get("tool_calls"):
            msgs.append(m)
            for tc in m["tool_calls"]:
                fn   = tc["function"]["name"]
                args = tc["function"]["arguments"]
                print(f"  ⚙  {fn}({args})")
                msgs.append({"role":"tool","content":DISPATCH[fn](**args)})
            continue
        history.append({"role":"assistant","content":m.get("content","")})
        return m.get("content","")


if __name__ == "__main__":
    history = load_session()
    print(f"Model: {MODEL}  |  Saved messages: {len(history)}\n")
    system_prompt = ""
    # Get the directory where agent.py is located
    script_dir = Path(__file__).parent
    # Construct the full path to the prompt file
    prompt_path = script_dir / "SystemPrompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as file:
        system_prompt = file.read()
    while True:
        u = input("you » ").strip()
        if u.startswith("/"):
            new_history, stop = handle_command(u, history)
            if stop:
                break
            history = new_history if new_history is not None else history
            continue
        print(f"agent » {run(u, history, system_prompt)}\n")
        save_session(history)              # ← this is the memory
