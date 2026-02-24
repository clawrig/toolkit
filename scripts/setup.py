#!/usr/bin/env python3
"""Claude Toolkit Setup — user-level tool installation. Stdlib only."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import (
    BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW,
    CLAUDEMAN_DIR, CLAUDEMAN_PORT,
    MAIL_DIR, MAIL_PORT, MAIL_TOKEN_FILE,
    check_claudeman_installed, check_mail_installed, check_mail_mcp,
    check_marketplace, check_mcp, check_plugin, claudeman_server_alive,
    command_exists, configure_serena, ensure_dep,
    generate_mail_token, log, mail_server_alive, read_mail_token, run,
    run_capture, start_claudeman, start_mail_server,
)

# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = {}


def tool(id_, name, description, check_fn, install_fn, uninstall_fn=None,
         deps=None, recommended=False, optional=False, per_project=False):
    TOOLS[id_] = {
        "name": name,
        "description": description,
        "check": check_fn,
        "install": install_fn,
        "uninstall": uninstall_fn,
        "deps": deps or [],
        "recommended": recommended,
        "optional": optional,
        "per_project": per_project,
    }


# --- Context7 ---
def _install_context7():
    # Migrate from old MCP-based install to plugin
    if check_mcp("context7"):
        log("  Migrating Context7 from MCP to plugin...")
        run("claude mcp remove --scope user context7")
    return run("claude plugin install context7@claude-plugins-official")

def _uninstall_context7():
    run("claude plugin uninstall context7")
    # Also clean up legacy MCP if present
    if check_mcp("context7"):
        run("claude mcp remove --scope user context7")

tool(
    "context7", "Context7", "Up-to-date library docs via MCP plugin",
    check_fn=lambda: check_plugin("context7"),
    install_fn=_install_context7,
    uninstall_fn=_uninstall_context7,
    recommended=True,
)

# --- Serena ---
def _install_serena():
    # Migrate from old MCP-based install to plugin
    if check_mcp("serena"):
        log("  Migrating Serena from MCP to plugin...")
        run("claude mcp remove --scope user serena")
    ok = ensure_dep("uvx", "uv (Python package manager)", {
        "darwin": 'curl -LsSf https://astral.sh/uv/install.sh | sh',
        "linux": 'curl -LsSf https://astral.sh/uv/install.sh | sh',
        "win32": 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
    })
    if not ok and not command_exists("uvx"):
        log("  Skipping Serena: uvx not available")
        return False
    result = run("claude plugin install serena@claude-plugins-official")
    if result:
        configure_serena()
    return result

def _uninstall_serena():
    run("claude plugin uninstall serena")
    # Also clean up legacy MCP if present
    if check_mcp("serena"):
        run("claude mcp remove --scope user serena")

tool(
    "serena", "Serena", "Semantic code navigation via LSP (30+ languages)",
    check_fn=lambda: check_plugin("serena"),
    install_fn=_install_serena,
    uninstall_fn=_uninstall_serena,
    deps=["uvx"],
    recommended=True,
)

# --- Dolt ---
tool(
    "dolt", "Dolt", "Git-for-data SQL server (required by Beads)",
    check_fn=lambda: command_exists("dolt"),
    install_fn=lambda: ensure_dep("dolt", "Dolt", {
        "darwin": "brew install dolt",
        "linux": 'sudo bash -c "curl -L https://github.com/dolthub/dolt/releases/latest/download/install.sh | bash"',
    }),
    uninstall_fn=lambda: run("brew uninstall dolt"),
    recommended=True,
)

# --- Beads ---
def _install_beads():
    ensure_dep("bd", "Beads CLI (bd)", {
        "darwin": "curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash",
        "linux": "curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash",
        "win32": "go install github.com/steveyegge/beads/cmd/bd@latest",
    })
    if not command_exists("bd"):
        log("  Skipping Beads plugin: bd CLI not available")
        return False
    if not check_marketplace("steveyegge/beads"):
        run("claude plugin marketplace add steveyegge/beads")
    return run("claude plugin install beads")

def _uninstall_beads():
    run("claude plugin uninstall beads")
    run("claude plugin marketplace remove beads-marketplace")

tool(
    "beads", "Beads", "Git-backed issue tracker + Claude plugin (30+ commands)",
    check_fn=lambda: command_exists("bd") and check_plugin("beads"),
    install_fn=_install_beads,
    uninstall_fn=_uninstall_beads,
    deps=["bd", "dolt"],
)

# --- beads-ui ---
tool(
    "beadsui", "beads-ui", "Browser UI for Beads issues (kanban, epics, search)",
    check_fn=lambda: command_exists("bdui"),
    install_fn=lambda: run("npm i -g beads-ui"),
    uninstall_fn=lambda: run("npm uninstall -g beads-ui"),
    deps=["npm"],
)

# --- Agent Mail ---
def _install_mail():
    ok = ensure_dep("uvx", "uv (Python package manager)", {
        "darwin": 'curl -LsSf https://astral.sh/uv/install.sh | sh',
        "linux": 'curl -LsSf https://astral.sh/uv/install.sh | sh',
        "win32": 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
    })
    if not ok and not command_exists("uvx"):
        log("  Skipping Agent Mail: uvx not available")
        return False

    # Clone repo (if not already present)
    if not os.path.isdir(MAIL_DIR):
        log("  Cloning mcp_agent_mail...")
        if not run(f"git clone --depth 1 https://github.com/Dicklesworthstone/mcp_agent_mail.git {MAIL_DIR}"):
            return False

    # Create venv and install deps (skip beads/bv — we have our own)
    log("  Setting up Python environment...")
    try:
        subprocess.run(
            "uv venv --python 3.13 && uv sync",
            shell=True, check=True, cwd=MAIL_DIR,
            capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        log(f"  Failed to set up environment: {e.stderr[:200] if e.stderr else 'unknown error'}")
        return False

    # Generate auth token
    token = read_mail_token()
    if not token:
        token = generate_mail_token()
        os.makedirs(os.path.dirname(MAIL_TOKEN_FILE), exist_ok=True)
        with open(MAIL_TOKEN_FILE, "w") as f:
            f.write(token)
        os.chmod(MAIL_TOKEN_FILE, 0o600)
        log("  Generated auth token")

    # Write .env for the server
    env_file = os.path.join(MAIL_DIR, ".env")
    with open(env_file, "w") as f:
        f.write(f"HTTP_PORT={MAIL_PORT}\n")
        f.write(f"HTTP_BEARER_TOKEN={token}\n")

    # Register MCP server in Claude Code (remove first if exists from prior install)
    log("  Registering MCP server...")
    if check_mcp("agent-mail"):
        run("claude mcp remove agent-mail --scope user")
    if not run(
        f'claude mcp add agent-mail http://localhost:{MAIL_PORT}/api/ '
        f'--scope user --transport http '
        f'-H "Authorization: Bearer {token}"'
    ):
        return False

    log(f"  Server installed at {MAIL_DIR}")
    log(f"  Start with: cd {MAIL_DIR} && uv run python -m mcp_agent_mail.cli serve-http")
    return True


def _uninstall_mail():
    run("claude mcp remove --scope user agent-mail")
    # Don't remove the repo — user may have data


tool(
    "mail", "Agent Mail", "Cross-project agent messaging via MCP (mcp_agent_mail)",
    check_fn=lambda: check_mail_installed() and check_mail_mcp(),
    install_fn=_install_mail,
    uninstall_fn=_uninstall_mail,
    deps=["uvx", "git"],
)

# --- Claudeman ---
def _install_claudeman():
    ok = ensure_dep("npm", "Node.js (npm)", {
        "darwin": "brew install node",
        "linux": "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs",
    })
    if not ok and not command_exists("npm"):
        log("  Skipping Claudeman: npm not available")
        return False
    if not ensure_dep("tmux", "tmux", {
        "darwin": "brew install tmux",
        "linux": "sudo apt-get install -y tmux",
    }):
        log("  Skipping Claudeman: tmux not available")
        return False
    if not os.path.isdir(CLAUDEMAN_DIR):
        log("  Cloning Claudeman...")
        if not run(f"git clone --depth 1 https://github.com/Ark0N/Claudeman.git {CLAUDEMAN_DIR}"):
            return False
    if not os.path.isdir(os.path.join(CLAUDEMAN_DIR, "node_modules")):
        log("  Installing dependencies...")
        if not run(f"npm install --prefix {CLAUDEMAN_DIR}"):
            return False
    if not os.path.isfile(os.path.join(CLAUDEMAN_DIR, "dist", "index.js")):
        log("  Building...")
        if not run(f"npm run build --prefix {CLAUDEMAN_DIR}", timeout=120):
            return False
    log(f"  Claudeman installed at {CLAUDEMAN_DIR}")
    log(f"  Start with: npm start --prefix {CLAUDEMAN_DIR}")
    return True

def _uninstall_claudeman():
    import shutil
    if os.path.isdir(CLAUDEMAN_DIR):
        shutil.rmtree(CLAUDEMAN_DIR)
        log(f"  Removed {CLAUDEMAN_DIR}")

tool(
    "claudeman", "Claudeman", "WebUI for Claude Code sessions (tmux, respawn, visualization)",
    check_fn=lambda: check_claudeman_installed(),
    install_fn=_install_claudeman,
    uninstall_fn=_uninstall_claudeman,
    deps=["npm", "tmux", "git"],
)

# --- BMAD ---
def _install_bmad():
    cwd = os.getcwd()
    if NON_INTERACTIVE or not sys.stdin.isatty():
        log("  Installing BMAD (non-interactive)...")
        cmd = (
            f'npx bmad-method install'
            f' --directory "{cwd}"'
            f' --modules bmm'
            f' --tools claude-code'
            f' --yes'
        )
    else:
        log("  Launching interactive BMAD installer...")
        cmd = "npx bmad-method install"
    r = subprocess.run(cmd, shell=True)
    if not os.path.isdir(os.path.join(cwd, "_bmad")):
        log("  BMAD installer finished but _bmad/ was not created.")
        log("  Run manually: npx bmad-method install")
        return False
    return r.returncode == 0

tool(
    "bmad", "BMAD-METHOD", "SDLC workflow framework (PM, Architect, Dev, QA personas)",
    check_fn=lambda: os.path.isdir(os.path.join(os.getcwd(), "_bmad")),
    install_fn=_install_bmad,
    deps=["npx"],
    optional=False,
    per_project=True,
)

# ── CLI args ──────────────────────────────────────────────────────────────────

args = sys.argv[1:]
NON_INTERACTIVE = "--non-interactive" in args
INSTALL_TARGET = None
if "--install" in args:
    idx = args.index("--install")
    if idx + 1 < len(args):
        INSTALL_TARGET = args[idx + 1]

# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    log()
    log(f"  {BOLD}Claude Toolkit Setup{RESET}")
    log(f"  {'=' * 20}")
    log()

    if not command_exists("claude"):
        log("Error: `claude` CLI not found.")
        log("Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code")
        sys.exit(1)

    log("Checking installed tools...")
    log()

    status = {}
    for id_, t in TOOLS.items():
        try:
            installed = t["check"]()
        except Exception:
            installed = False

        missing_deps = [d for d in t["deps"] if not command_exists(d)]
        status[id_] = {"installed": installed, "missing_deps": missing_deps}

        icon = f"{GREEN}✓{RESET}" if installed else f"{DIM}·{RESET}"
        line = f"  {icon} {id_:<10} {t['name']} — {t['description']}"
        if missing_deps:
            line += f" {YELLOW}(needs: {', '.join(missing_deps)}){RESET}"
        if t["recommended"]:
            line += f" {CYAN}[recommended]{RESET}"
        if t["optional"]:
            line += f" {DIM}[optional]{RESET}"
        elif t["per_project"]:
            line += f" {DIM}[per-project]{RESET}"
        log(line)

    # Ensure mail server is running (if installed)
    if check_mail_installed() and not mail_server_alive():
        log("Starting Agent Mail server...")
        if start_mail_server():
            log(f"  {GREEN}✓{RESET} Agent Mail running on port {MAIL_PORT}")
        else:
            log(f"  {YELLOW}!{RESET} Failed to start (check ~/.mcp_agent_mail/server.log)")

    # Ensure Claudeman is running (if installed)
    if check_claudeman_installed() and not claudeman_server_alive():
        log("Starting Claudeman...")
        if start_claudeman():
            log(f"  {GREEN}✓{RESET} Claudeman running on port {CLAUDEMAN_PORT}")
        else:
            log(f"  {YELLOW}!{RESET} Failed to start (check ~/.claudeman/server.log)")

    log()

    # Determine what to install
    not_installed = [id_ for id_, t in TOOLS.items()
                     if not status[id_]["installed"] and not t["optional"]]
    not_installed_opt = [id_ for id_, t in TOOLS.items()
                         if not status[id_]["installed"] and t["optional"]]

    if not not_installed and not not_installed_opt:
        log("All tools are already installed!")
        return

    if INSTALL_TARGET:
        selected = [INSTALL_TARGET]
    elif NON_INTERACTIVE:
        selected = not_installed
        if not selected:
            log("All standard tools are already installed!")
            return
    else:
        available = not_installed + not_installed_opt
        log(f"Available: {', '.join(available)}")
        if not_installed_opt:
            log(f"{DIM}  Optional (not included in \"all\" — install by name): {', '.join(not_installed_opt)}{RESET}")
        try:
            answer = input('Install (space-separated IDs, "all", or "q" to quit): ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            log("\nCancelled.")
            sys.exit(0)
        if not answer or answer == "q":
            log("Cancelled.")
            sys.exit(0)
        selected = not_installed if answer == "all" else answer.split()

    # Install
    results = {"ok": [], "skip": [], "fail": []}
    for id_ in selected:
        t = TOOLS.get(id_)
        if not t:
            log(f"\nUnknown tool: {id_}")
            results["fail"].append(id_)
            continue
        if status.get(id_, {}).get("installed"):
            log(f"\n✓ {t['name']} already installed, skipping")
            results["skip"].append(id_)
            continue
        log(f"\nInstalling {t['name']}...")
        ok = t["install"]()
        if ok is False:
            results["fail"].append(id_)
            log(f"✗ {t['name']} failed")
        else:
            results["ok"].append(id_)
            log(f"✓ {t['name']} done")

    # Summary
    log()
    log(f"  {BOLD}Setup complete!{RESET}")
    log("  ───────────────")
    if results["ok"]:
        log(f"  Installed: {', '.join(results['ok'])}")
    if results["skip"]:
        log(f"  Skipped:   {', '.join(results['skip'])}")
    if results["fail"]:
        log(f"  Failed:    {', '.join(results['fail'])}")
    log()
    log("  Restart Claude Code for MCP servers to connect.")
    log("  Verify with: claude mcp list")
    log()


if __name__ == "__main__":
    main()
