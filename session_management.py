from pathlib import Path
import json, ollama, uuid
from model import MODEL

MEMO         = Path.home() / "personal_agent" / "agent_memory"
MEMO.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR = MEMO / "sessions"               # one JSON file per session (uuid.json)
SESSIONS_DIR.mkdir(exist_ok=True)
INDEX        = MEMO / "conversations.json"     # { name: "uuid.json", "current": "uuid.json" }
CURRENT      = "current"


# --- low-level file helpers -------------------------------------------------

def _write(path, data):
    path.write_text(json.dumps(data, indent=2))

def _new_uuid_file(msgs=None):
    """Create a fresh sessions/<uuid>.json and return its filename."""
    fname = uuid.uuid4().hex + ".json"
    _write(_session_path(fname), msgs if msgs is not None else [])
    return fname

def _session_path(fname):
    return SESSIONS_DIR / fname

def _read(fname):
    p = _session_path(fname)
    return json.loads(p.read_text()) if p.exists() else []

def _delete_file(fname):
    p = _session_path(fname)
    if p.exists():
        p.unlink()


# --- index (conversations.json) --------------------------------------------

def load_all():
    """Return the index as { name: "uuid.json", "current": "uuid.json" }."""
    return json.loads(INDEX.read_text()) if INDEX.exists() else {}

def save_index(idx):
    _write(INDEX, idx)

def _unique_name(idx, name):
    if name != CURRENT and name not in idx:
        return name
    i = 2
    while f"{name}_{i}" in idx:
        i += 1
    return f"{name}_{i}"


# --- public API (signatures unchanged for command_registry / agent.py) ------

def load_session(key=CURRENT):
    """Load the live conversation, or absorb a named session into current.

    Absorb: repoint 'current' at the named session's file, then drop the
    named entry (matching the old delete-on-load behavior).
    """
    idx = load_all()
    if key == CURRENT:
        fname = idx.get(CURRENT) or _new_uuid_file()
        idx[CURRENT] = fname
        save_index(idx)
        return _read(fname)

    if key in idx:
        src = idx[key]
        del idx[key]
        idx[CURRENT] = src
        save_index(idx)
        return _read(src)
    return []

def save_session(msgs, key=CURRENT):
    idx = load_all()
    fname = idx.get(key) or _new_uuid_file()
    idx[key] = fname
    save_index(idx)
    _write(_session_path(fname), msgs)

def rename_session(new_key):
    """Name the current session's file under `new_key`, then start a fresh current."""
    idx = load_all()
    current_file = idx.get(CURRENT) or _new_uuid_file()
    idx[CURRENT] = current_file
    new_key = _unique_name(idx, new_key)
    idx[new_key] = current_file
    idx[CURRENT] = _new_uuid_file()
    save_index(idx)

def clear_session(msgs):
    """Persist the live conversation under an LLM-chosen name, then go blank."""
    name = get_session_name(msgs)
    idx = load_all()
    current_file = idx.get(CURRENT) or _new_uuid_file()
    _write(_session_path(current_file), msgs)   # make sure latest msgs are saved
    rename_session(name)

def list_sessions():
    idx = load_all()
    return [k for k in idx if k != CURRENT]

def delete_session(key=None):
    if key is None:
        import shutil
        shutil.rmtree(SESSIONS_DIR, ignore_errors=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        idx = {}
        save_index(idx)
        idx[CURRENT] = _new_uuid_file()
        save_index(idx)
        return
    idx = load_all()
    if key in idx and key != CURRENT:
        _delete_file(idx[key])
        del idx[key]
        save_index(idx)

def get_session_name(msgs):
    """Ask the model for a 2-3 word name for this conversation."""
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content":
                    "I want to store these messages against a session name.Give this conversation one name. "
                    "Reply with only the name, nothing else."
                    "The name can be separated into at MAX 4 words, separated by an underscore. The name should be a concise description of the conversation."},
                {"role": "user", "content":
                    f"Conversation: {json.dumps(msgs[-4:], default=str)[:2000]}"},
            ],
            stream=False,
        )
        return resp["message"]["content"].strip().split("\n")[0]
    except Exception:
        return "last_session"
