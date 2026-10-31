from pathlib import Path
import json, ollama
from model import MODEL

MEMO   = Path.home() / "personal_agent" / "agent_memory"
MEMO.mkdir(exist_ok=True)
HIST   = MEMO / "conversations.json"          # the one file that holds your memory

def load_all():
    all_conversations = json.loads(HIST.read_text()) if HIST.exists() else {}
    return all_conversations

def load_session(key="current"):
    all_conversations = load_all()
    load_history = []
    if key != "current" and key in all_conversations:
        clear_session(all_conversations.get("current", []))
        all_conversations = load_all()
        load_history = all_conversations.get(key, [])
        all_conversations["current"] = load_history
        del all_conversations[key]
        save_all(all_conversations)
    return load_history

def save_all(data):
    HIST.write_text(json.dumps(data, indent=2))

def save_session(msgs, key="current"):
    all = load_all()
    all[key] = msgs
    save_all(all)

def rename_session(new_key, msgs):
    all = load_all()
    all[new_key] = msgs
    if "current" in all:
        del all["current"]
    save_all(all)

def list_sessions():
    all_conversations = load_all()
    return list(all_conversations.keys())

def clear_session(msgs):
    key = get_session_name(msgs)
    rename_session(key, msgs)

def delete_session(key = None):
    all_conversations = load_all()
    if key is None:
        all_conversations = {}
    elif key in all_conversations:
        del all_conversations[key]
    save_all(all_conversations)

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
