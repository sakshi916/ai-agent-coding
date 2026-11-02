import platform, os
from pathlib import Path
from fnmatch import fnmatch

# The folder the terminal is open in (set at runtime)
ALLOWED_FOLDER = [Path.cwd().resolve()]

def get_system_paths() -> list[str]:
    system = platform.system()
    if system == "Darwin":
        return ["/System", "/Library", "/private",
                "/coreservices", "/corespotlight"]
    elif system == "Linux":
        return ["/bin", "/sbin", "/usr", "/etc", "/var",
                "/boot", "/run", "/proc", "/sys", "/dev"]
    elif system == "Windows":
        return [
            os.environ.get("WINDIR", r"C:\Windows"),
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("ProgramData", r"C:\ProgramData"),
        ]
    return []  # unknown OS → deny by default


def _is_system_path(p: Path) -> bool:
    for sys_path in get_system_paths():
        prefix = sys_path.rstrip("/")
        if str(p) == prefix or str(p).startswith(prefix + "/"):
            return True
    return False



def validate_path(path):
    p = Path(path).resolve()
    p = p.parent if p.is_file() or not p.exists() else p
    # 1. Block system paths — is this path INSIDE a system dir?
    if _is_system_path(p):
        return f"❌ Access to system path blocked: {p}"

    # 2. Prompt permission if outside the terminal's folder
    if not any(p.is_relative_to(folder) for folder in ALLOWED_FOLDER):
        print(f"\n⚠️  Path '{p}' is outside your working folder '{ALLOWED_FOLDER}'.")
        resp = input("    Allow grep/search on this path? [y/N]: ").strip().lower()
        if resp != "y":
            return f"❌ Permission denied for path: {p}"
        print(f"    ✅ Access granted for {p}")
        ALLOWED_FOLDER.append(p)  # allow this folder for future searches
    return None


# Hard-blocked sensitive filenames — glob patterns matched against the
# basename (case-insensitive on POSIX, as on Windows).
SENSITIVE_PATTERNS = [
    ".env", ".env.*",
    "*.pem", "*.key", "*.p12", "*.pfx",
    "secrets", "secrets.*",
    "credentials", "credentials.*",
    ".gitconfig", ".git-credentials",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    ".git",                       # ← add this
    ".gitignore",                 # ← optional, some people want to keep it
]


# ── Write-specific validation (stricter than reads) ──────────────────────────
def validate_write_path(path) -> str | None:
    """Return an error string, or None if the path is safe to write.

    Unlike validate_path() from validation.py:
      • Outside-workspace paths are DENIED (no interactive prompt).
      • Sensitive filenames are DENIED (no interactive prompt).
      • System paths are still blocked via _is_system_path().
    """
    p = Path(path).resolve()

    # 1. System path block — same as reads
    if _is_system_path(p):
        return f"❌ System path blocked: {p}"

    # 2. Must be inside the workspace — no prompt, hard deny
    if not p.is_relative_to(Path.cwd().resolve()):
        return (f"❌ Write blocked: '{p}' is outside workspace ")

    # 3. Sensitive file block — hard deny
    name = p.name.lower()
    for pattern in SENSITIVE_PATTERNS:
        if fnmatch(name, pattern):
            return f"❌ Cannot write to sensitive file: '{p.name}'"

    return None
