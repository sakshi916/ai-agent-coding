import platform, os
from pathlib import Path

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
