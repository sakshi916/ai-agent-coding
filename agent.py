import ollama
from pathlib import Path
from read_tools import TOOLS, DISPATCH
from session_management import load_session, save_session, clear_session, list_sessions, delete_session
from model import MODEL

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
        print("------------message------------", m)
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
    with open("SystemPrompt.txt", "r", encoding="utf-8") as file:
        system_prompt = file.read()
    while True:
        u = input("you » ").strip()
        if u.startswith("/"):
            if u == "/clear":
                clear_session(history)
                history = []
                print("Cleared history.")
                continue
            elif u == "/exit":
                clear_session(history)
                print("Saved. Bye.")
                break
            elif u.startswith("/load "):
                save_session(history)              # ← this is the memory
                key = u.split(" ",1)[1].strip()
                history = load_session(key)
                print(f"Loaded '{key}' ({len(history)} msgs)")
                continue
            elif u == "/list":
                print("Available conversations:")
                for key in list_sessions():
                    print(f"  - {key}")
                continue
            elif u == "/deleteAll":
                delete_session()
                history = []
                print("All sessions deleted.")
                continue
            elif u.startswith("/delete "):
                key = u.split(" ",1)[1].strip()
                delete_session(key)
                history = []
                print(f"Deleted session '{key}'.")
                continue
            else:
                print("Commands: /load, /clear, /exit")
        print(f"agent » {run(u, history, system_prompt)}\n")
        save_session(history)              # ← this is the memory
