import json, os, ollama
from pathlib import Path

MODEL  = "qwen3.8:27b-mlx"                        # ← change if you pulled a different model
MEMO   = Path.home() / "personal_agent" / "agent_memory"
HIST   = MEMO / "conversations.json"          # the one file that holds your memory
MEMO.mkdir(exist_ok=True)

def load_history():
    return json.loads(HIST.read_text()) if HIST.exists() else []

def save_history(msgs):
    HIST.write_text(json.dumps(msgs, indent=2))

# ── the three things the agent can do ──────────────────────────────────
def list_folder(path, depth=2):
    root = Path(path)
    if not root.is_dir():
        return f"Error: not a folder: {path}"
    out = [str(root) + "/"]
    for f in sorted(root.rglob("*")):
        d = len(f.relative_to(root).parts) - 1
        if d >= depth:
            continue
        icon = "📁" if f.is_dir() else "📄"
        out.append("  " * d + icon + " " + f.name)
    return "\n".join(out[:200])

def read_file(path, max_chars=6000):
    p = Path(path)
    if not p.is_file():
        return f"Error: not a file: {path}"
    t = p.read_text(errors="replace")
    return t[:max_chars] + ("…[truncated]" if len(t) > max_chars else "")

def search_folder(path, query, limit=15):
    root = Path(path)
    hits = []
    for f in root.rglob("*"):
        if f.is_file():
            try:
                for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                    if query.lower() in line.lower():
                        hits.append(f"{f.name}:{i}: {line.strip()[:150]}")
                        if len(hits) >= limit:
                            return "\n".join(hits)
            except:
                pass
    return "No matches." if not hits else "\n".join(hits)

TOOLS = [
    {"type":"function","function":{
        "name":"list_folder",
        "description":"List folders and files in a directory.",
        "parameters":{"type":"object",
            "properties":{"path":{"type":"string"}},
            "required":["path"]}}},
    {"type":"function","function":{
        "name":"read_file",
        "description":"Read the contents of a file.",
        "parameters":{"type":"object",
            "properties":{"path":{"type":"string"}},
            "required":["path"]}}},
    {"type":"function","function":{
        "name":"search_folder",
        "description":"Search all text files in a folder for a keyword.",
        "parameters":{"type":"object",
            "properties":{"path":{"type":"string"},
                          "query":{"type":"string"}},
            "required":["path","query"]}}},
]
DISPATCH = {"list_folder": list_folder, "read_file": read_file, "search_folder": search_folder}
 
def run(user_msg, history, folder):
    history.append({"role":"user","content":user_msg})
    msgs = [
        {"role":"system","content":
         f"You are a local assistant. The user's folder is {folder}. "
         f"Use the tools to explore it. Be concise."},
        *history[-40:]                      # keep last 40 messages in context
    ]
    for _ in range(8):
        resp = ollama.chat(model=MODEL, messages=msgs, tools=TOOLS)
        m = resp["message"]
        print("m----------",m)
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
    folder  = input("Folder path: ").strip()
    history = load_history()
    print(f"Model: {MODEL}  |  Saved messages: {len(history)}\n")
    while True:
        u = input("you » ").strip()
        if u in ("quit","exit"):
            save_history(history); print("Saved. Bye."); break
        print(f"agent » {run(u, history, folder)}\n")
        save_history(history)              # ← this is the memory
