from session_management import (
    load_session, save_session, clear_session, list_sessions, delete_session
)

# --- command handlers: each returns (new_history_or_None, should_break) ---

def _cmd_clear(history, u):
    clear_session(history)
    print("Cleared history.")
    return [], False

def _cmd_exit(history, u):
    clear_session(history)
    print("Saved. Bye.")
    return None, True

def _cmd_load(history, u):
    save_session(history)
    key = u.split(" ", 1)[1].strip()
    new = load_session(key)
    print(f"Loaded '{key}' ({len(new)} msgs)")
    return new, False

def _cmd_list(history, u):
    print("Available conversations:")
    for key in list_sessions():
        print(f"  - {key}")
    return None, False

def _cmd_deleteall(history, u):
    delete_session()
    print("All sessions deleted.")
    return [], False

def _cmd_delete(history, u):
    key = u.split(" ", 1)[1].strip()
    delete_session(key)
    print(f"Deleted session '{key}'.")
    return [], False

EXACT = {
    "/clear":     _cmd_clear,
    "/exit":      _cmd_exit,
    "/list":      _cmd_list,
    "/deleteAll": _cmd_deleteall,
}
PREFIX = {
    "/load ":    _cmd_load,
    "/delete ":  _cmd_delete,
}

def handle_command(u, history):
    handler = EXACT.get(u)
    if handler is None:
        for prefix, h in PREFIX.items():
            if u.startswith(prefix):
                handler = h
                break
    if handler is None:
        print("Commands: /load, /clear, /exit, /list, /delete, /deleteAll")
        return history, False
    return handler(history, u)
