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
OPTIONS = {"temperature": 0.2,
           # "num_ctx": 4000
           }
MAX_ITER = 15

def run(user_msg, history, system_prompt):
    history.append({"role":"user","content":user_msg})
    msgs = [
        {"role":"system","content":
         f"You are a local coding assistant. Working in this workspace:{Path.cwd()}.\n" + system_prompt},
        *history[-20:]                      # keep last 20 messages in context
    ]
    for i in range(MAX_ITER):
        # Nudge the model to wrap up on the second-to-last iteration
        if i == MAX_ITER - 2:
            msgs.append({"role":"user","content":
                "You have used most of your tool calls. Stop exploring. "
                "Summarize what you found from the files and searches already in your "
                "conversation history and give your final answer now."})

        resp = ollama.chat(model=MODEL, messages=msgs, tools=TOOLS, options=OPTIONS)
        m = resp["message"]

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

    # Loop exhausted without a final text response
    fallback = ("Reached max tool-call iterations without a final answer. "
                "Try rephrasing or breaking the task into smaller steps.")
    history.append({"role":"assistant","content":fallback})
    return fallback


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
