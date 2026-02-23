"""Shared helpers for toolkit scripts. Stdlib only, zero external deps."""

import json
import os
import re
import shutil
import subprocess
import sys

# ── Colors ────────────────────────────────────────────────────────────────────

_NO_COLOR = os.environ.get("NO_COLOR") or not sys.stdout.isatty()

GREEN = "" if _NO_COLOR else "\033[32m"
DIM = "" if _NO_COLOR else "\033[90m"
YELLOW = "" if _NO_COLOR else "\033[33m"
CYAN = "" if _NO_COLOR else "\033[36m"
RED = "" if _NO_COLOR else "\033[31m"
BOLD = "" if _NO_COLOR else "\033[1m"
RESET = "" if _NO_COLOR else "\033[0m"

# ── Logging ───────────────────────────────────────────────────────────────────


def log(msg=""):
    print(msg)


# ── Command helpers ───────────────────────────────────────────────────────────


def command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run(cmd: str, timeout: int = 60, **kwargs) -> bool:
    """Run command with inherited stdio. Returns True on success."""
    try:
        subprocess.run(cmd, shell=True, check=True, timeout=timeout, **kwargs)
        return True
    except subprocess.TimeoutExpired:
        log(f"  Warning: command timed out ({timeout}s): {cmd}")
        return False
    except subprocess.CalledProcessError:
        log(f"  Warning: command failed: {cmd}")
        return False


def run_capture(cmd: str, timeout: int = 10) -> str | None:
    """Run command and return stdout, or None on failure/timeout."""
    try:
        r = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True,
            timeout=timeout,
        )
        return r.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


# ── Claude config paths ──────────────────────────────────────────────────────

_CLAUDE_DIR = os.path.join(os.path.expanduser("~"), ".claude")
_PLUGINS_JSON = os.path.join(_CLAUDE_DIR, "plugins", "installed_plugins.json")
_SETTINGS_JSON = os.path.join(_CLAUDE_DIR, "settings.json")
_MARKETPLACES_JSON = os.path.join(_CLAUDE_DIR, "plugins", "known_marketplaces.json")


def _read_json(path: str) -> dict:
    """Read a JSON file, returning empty dict on any failure."""
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def check_mcp(name: str) -> bool:
    """Check if an MCP server is configured (reads settings.json directly)."""
    data = _read_json(_SETTINGS_JSON)
    servers = data.get("mcpServers", {})
    return name.lower() in (k.lower() for k in servers)


def check_plugin(name: str) -> bool:
    """Check if a plugin is installed (reads installed_plugins.json directly)."""
    data = _read_json(_PLUGINS_JSON)
    plugins = data.get("plugins", {})
    needle = name.lower()
    return any(needle in key.lower() for key in plugins)


def check_marketplace(name: str) -> bool:
    """Check if a marketplace is registered (reads known_marketplaces.json directly)."""
    data = _read_json(_MARKETPLACES_JSON)
    needle = name.lower()
    for key, val in data.items():
        if needle in key.lower():
            return True
        # Also check source repo field (e.g. "steveyegge/beads")
        repo = (val.get("source", {}).get("repo", "") or
                val.get("source", {}).get("url", ""))
        if needle in repo.lower():
            return True
    return False


# ── Serena config ─────────────────────────────────────────────────────────────


def configure_serena():
    config_path = os.path.join(os.path.expanduser("~"), ".serena", "serena_config.yml")
    if not os.path.isfile(config_path):
        return
    try:
        content = open(config_path).read()
        if re.search(r"^web_dashboard_open_on_launch:\s*true\s*$", content, re.M):
            content = re.sub(
                r"^web_dashboard_open_on_launch:\s*true\s*$",
                "web_dashboard_open_on_launch: false",
                content,
                flags=re.M,
            )
            with open(config_path, "w") as f:
                f.write(content)
            log("  Configured Serena: web_dashboard_open_on_launch = false")
    except OSError:
        pass


# ── Agent Mail helpers ────────────────────────────────────────────────────────

MAIL_DIR = os.path.join(os.path.expanduser("~"), ".mcp_agent_mail")
MAIL_TOKEN_FILE = os.path.join(MAIL_DIR, ".auth_token")
MAIL_PORT = 8765


def check_mail_installed() -> bool:
    """Check if mcp_agent_mail is installed (repo cloned + venv exists)."""
    return os.path.isdir(os.path.join(MAIL_DIR, ".venv"))


def check_mail_mcp() -> bool:
    """Check if agent-mail MCP server is configured in Claude Code."""
    return check_mcp("agent-mail")


def read_mail_token() -> str | None:
    """Read the stored auth token."""
    if os.path.isfile(MAIL_TOKEN_FILE):
        return open(MAIL_TOKEN_FILE).read().strip()
    return None


def generate_mail_token() -> str:
    """Generate a random auth token for the mail server."""
    import secrets
    return secrets.token_hex(32)


def mail_server_alive() -> bool:
    """Check if the mail server is responding."""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(f"http://localhost:{MAIL_PORT}/health/liveness")
        urllib.request.urlopen(req, timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


def start_mail_server() -> bool:
    """Start the mail server in the background. Returns True if started or already running."""
    if mail_server_alive():
        return True
    if not check_mail_installed():
        return False
    import time
    pid_file = os.path.join(MAIL_DIR, ".server.pid")
    subprocess.Popen(
        ["uv", "run", "python", "-m", "mcp_agent_mail.cli", "serve-http"],
        cwd=MAIL_DIR,
        stdout=open(os.path.join(MAIL_DIR, "server.log"), "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    # Wait briefly for startup
    for _ in range(6):
        time.sleep(1)
        if mail_server_alive():
            return True
    return False


# ── Claudeman helpers ────────────────────────────────────────────────────────

CLAUDEMAN_DIR = os.path.join(os.path.expanduser("~"), ".claudeman")
CLAUDEMAN_PORT = 3000


def check_claudeman_installed() -> bool:
    """Check if Claudeman is installed (repo cloned + node_modules exists)."""
    return os.path.isdir(os.path.join(CLAUDEMAN_DIR, "node_modules"))


def claudeman_server_alive() -> bool:
    """Check if Claudeman web UI is responding."""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(f"http://localhost:{CLAUDEMAN_PORT}/")
        urllib.request.urlopen(req, timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


def start_claudeman() -> bool:
    """Start Claudeman server in the background."""
    if claudeman_server_alive():
        return True
    if not check_claudeman_installed():
        return False
    import time
    subprocess.Popen(
        ["npm", "start"],
        cwd=CLAUDEMAN_DIR,
        stdout=open(os.path.join(CLAUDEMAN_DIR, "server.log"), "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(6):
        time.sleep(1)
        if claudeman_server_alive():
            return True
    return False


# ── Dep installation ──────────────────────────────────────────────────────────

PLATFORM = sys.platform  # darwin, linux, win32


def ensure_dep(cmd: str, name: str, installers: dict[str, str]) -> bool:
    """Ensure a CLI dependency is available, installing if possible."""
    if command_exists(cmd):
        return True
    install_cmd = installers.get(PLATFORM)
    if not install_cmd:
        log(f"  Cannot auto-install {name} on {PLATFORM}. Install manually.")
        return False
    log(f"  Installing {name}...")
    return run(install_cmd)


# ── Git helpers ───────────────────────────────────────────────────────────────


def git_remote_url(cwd: str | None = None) -> str | None:
    """Get git remote origin URL for the given directory."""
    cmd = "git remote get-url origin"
    try:
        r = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True,
            cwd=cwd,
        )
        return r.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def detect_repo_host(remote_url: str) -> str | None:
    """Detect tracker type from git remote URL."""
    if not remote_url:
        return None
    url = remote_url.lower()
    if "github.com" in url:
        return "github"
    if "gitlab" in url:
        return "gitlab"
    if "bitbucket" in url:
        return "bitbucket"
    return None


def extract_org_repo(remote_url: str) -> str | None:
    """Extract 'org/repo' from a git remote URL."""
    if not remote_url:
        return None
    # SSH: git@github.com:org/repo.git
    m = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", remote_url)
    return m.group(1) if m else None


# ── Marker file (auto-setup TTL) ─────────────────────────────────────────────

MARKER_PATH = os.path.join(os.path.expanduser("~"), ".claude", ".toolkit-setup-done")
MAX_AGE_DAYS = 7


def marker_is_fresh() -> bool:
    """Check if the auto-setup marker exists and is less than MAX_AGE_DAYS old."""
    if not os.path.isfile(MARKER_PATH):
        return False
    import time
    age_days = (time.time() - os.path.getmtime(MARKER_PATH)) / 86400
    return age_days < MAX_AGE_DAYS


def touch_marker():
    os.makedirs(os.path.dirname(MARKER_PATH), exist_ok=True)
    open(MARKER_PATH, "w").close()


def marker_mtime_str() -> str | None:
    """Return human-readable mtime of the marker file."""
    if not os.path.isfile(MARKER_PATH):
        return None
    import time
    t = os.path.getmtime(MARKER_PATH)
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))
