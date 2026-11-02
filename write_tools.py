import os
import tempfile
from pathlib import Path
from validation import validate_write_path
import shutil


# ── Constants ────────────────────────────────────────────────────────────────
MAX_WRITE_SIZE = 5 * 1024 * 1024  # 5 MB hard cap on content size


# ── Atomic write helper ───────────────────────────────────────────────────────
def atomic_write(path: str, content: str) -> str:
    """Write `content` to `path` atomically.

    Steps:
      1. Create a temp file in the *same directory* (same filesystem).
      2. Write + flush + fsync the temp file.
      3. os.replace() — atomic on POSIX and Windows 10+.
      4. On any error, clean up the temp file.
    """
    target = Path(path)
    content_bytes = content.encode("utf-8")

    # Size guard
    if len(content_bytes) > MAX_WRITE_SIZE:
        mb = len(content_bytes) / (1024 * 1024)
        return f"❌ Content is {mb:.1f} MB, exceeds MAX_WRITE_SIZE " \
               f"({MAX_WRITE_SIZE // (1024*1024)} MB)."

    # Ensure parent dir exists
    target.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in the same directory
    fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))   # atomic rename
    except Exception as e:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return f"❌ Write failed: {e}"

    return f"✅ Wrote {len(content_bytes)} bytes to '{target}'"


# ── Tool functions ────────────────────────────────────────────────────────────
def write_file(path: str, content: str) -> str:
    """Create or overwrite a file with the given content."""
    err = validate_write_path(path)
    if err:
        return err
    return atomic_write(path, content)


def create_file(path: str, content: str) -> str:
    """Create a new file. Fails if the file already exists."""
    err = validate_write_path(path)
    if err:
        return err
    if Path(path).exists():
        return f"❌ File already exists: '{Path(path)}'. " \
               f"Use write_file to overwrite."
    return atomic_write(path, content)

# ── patch_file ───────────────────────────────────────────────────────────────
def patch_file(path: str, old_text: str, new_text: str, occurrences: int = 1) -> str:
    """Replace a section of a file without rewriting the whole thing.

    Args:
        path:        Path to the file to patch.
        old_text:    Exact string to find (must match literally).
        new_text:    Replacement string. Pass "" to delete the section.
        occurrences: 1 = replace first match (default),
                     -1 = replace ALL matches,
                     N  = replace first N matches.
    """
    err = validate_write_path(path)
    if err:
        return err

    target = Path(path)

    # File must already exist to patch
    if not target.exists():
        return f"❌ File not found: '{target}'. Use create_file instead."

    content = target.read_text(encoding="utf-8")

    # Count matches
    count = content.count(old_text)
    if count == 0:
        # Help the model self-correct by showing a snippet near a partial match
        hint = _find_nearby(content, old_text)
        return (f"❌ '{old_text[:80]}...' not found in '{target.name}'.\n"
                f"{hint}\n"
                f"Read the file first with read_file to get the exact text.")

    # Decide how many to replace
    if occurrences == -1:
        replace_count = count
    else:
        replace_count = min(occurrences, count)

    # Perform replacement (left-to-right, non-overlapping)
    result = content.replace(old_text, new_text, replace_count)

    # Write atomically
    write_result = atomic_write(str(target), result)
    if write_result.startswith("❌"):
        return write_result

    verb = "deleted" if new_text == "" else "replaced"
    return (f"✅ Patched '{target.name}': {verb} {replace_count} "
            f"occurrence{'s' if replace_count != 1 else ''} "
            f"({count} total match{'es' if count != 1 else ''}).")

def delete_file(path: str) -> str:
    err = validate_write_path(path)
    if err:
        return err

    target = Path(path)
    if not target.exists():
        return f"❌ Not found: '{target}'."

    # ── Build a confirmation message that scales with the blast radius ──
    if target.is_dir():
        file_count = sum(1 for _ in target.rglob("*") if _.is_file())
        prompt = (f"Delete folder '{target.name}/' and "
                  f"{file_count} file{'s' if file_count != 1 else ''} "
                  f"inside it? (y/N)")
    else:
        prompt = f"Delete '{target.name}'? (y/N)"

    confirm = input(prompt).strip().lower()
    if confirm != "y":
        return "Aborted."

    # ── Execute ──
    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    except OSError as e:
        return f"❌ Delete failed: {e}"

    action = "Removed folder" if target.is_dir() else "Deleted"
    return f"✅ {action} '{target}'."


def _find_nearby(content: str, old_text: str, window: int = 120) -> str:
    """Best-effort hint: show a snippet where a *partial* match might be.

    Compares the first 20 chars of old_text to find the closest region.
    Returns a short context string for the error message.
    """
    key = old_text[:20]
    idx = content.find(key)
    if idx == -1:
        # Try progressively shorter prefixes
        for length in (15, 10, 5):
            idx = content.find(old_text[:length])
            if idx != -1:
                break

    if idx == -1:
        return "  No similar text found in file."

    start = max(0, idx - 30)
    end = min(len(content), idx + window)
    snippet = content[start:end].replace("\n", "\\n")
    return f"  Near miss at offset {idx}:\n  ...{snippet}..."

# ── OpenAI-style tool registry ───────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given "
                           "content. Writes are atomic and capped at "
                           "{MAX_WRITE_SIZE} MB. Cannot write to system paths or "
                           "sensitive files (.env, *.key, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string",
                                "description": "Path to the file to "
                                               "write (relative to "
                                               "workspace root)."},
                    "content": {"type": "string",
                                "description": "Full content to write "
                                               "to the file."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file. Fails if the file "
                           "already exists. Use write_file to "
                           "overwrite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patch_file",
            "description": (
                "Replace a section of an existing file without rewriting it. "
                "old_text must match the file content exactly (character for "
                "character, including whitespace). Use read_file first to get "
                "the exact text. Set occurrences=-1 to replace all matches. "
                "Set new_text='' to delete the section."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to patch.",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to find in the file.",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text. Empty string to delete.",
                    },
                    "occurrences": {
                        "type": "integer",
                        "description": "1 = first match (default), -1 = all, N = first N.",
                        "default": 1,
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete existing file or folder "
                            "If folder, all its contents will be deleted.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string"},
                },
                "required": ["path"],
            },
        },
    },
]

DISPATCH = {
    "write_file":  write_file,
    "create_file": create_file,
    "patch_file": patch_file,
    "delete_file":delete_file
}
