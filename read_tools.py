from pathlib import Path
from validation import validate_path

# ── the three things the agent can do ──────────────────────────────────
def list_folder(path, depth=2):
    err = validate_path(path)
    if err:
        return err
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
    err=validate_path(path)
    if err:
        return err
    p = Path(path)
    if not p.is_file():
        return f"Error: not a file: {path}"
    t = p.read_text(errors="replace")
    return t[:max_chars] + ("…[truncated]" if len(t) > max_chars else "")

def search_folder(path, query, limit=15):
    err = validate_path(path)
    if err:
        return err
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
