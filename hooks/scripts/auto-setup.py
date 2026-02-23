#!/usr/bin/env python3
"""SessionStart hook — auto-setup missing tools (non-interactive, 7-day TTL)."""

import os
import subprocess
import sys

# Add scripts/ to path so we can import lib
scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(scripts_dir))

from lib import (
    CLAUDEMAN_DIR, CLAUDEMAN_PORT,
    MAIL_DIR, MAIL_PORT,
    check_claudeman_installed, check_mail_installed, check_mail_mcp,
    check_mcp, check_plugin, claudeman_server_alive,
    command_exists, configure_serena, generate_mail_token,
    log, mail_server_alive, marker_is_fresh, read_mail_token, run,
    start_claudeman, start_mail_server, touch_marker, MAIL_TOKEN_FILE,
)

def main():
    # Always ensure mail server is running (if installed)
    if check_mail_installed() and not mail_server_alive():
        if start_mail_server():
            log("Toolkit: Agent Mail server started")

    # Always ensure Claudeman is running (if installed)
    if check_claudeman_installed() and not claudeman_server_alive():
        if start_claudeman():
            log("Toolkit: Claudeman server started")

    # Skip tool installation if marker is fresh
    if marker_is_fresh():
        return

    if not command_exists("claude"):
        return

    missing = []
    installed = []

    # --- Context7 ---
    # Migrate from old MCP-based install to plugin
    if check_mcp("context7") and not check_plugin("context7"):
        log("Migrating Context7 from MCP to plugin...")
        run("claude mcp remove --scope user context7")
    if check_plugin("context7"):
        installed.append("Context7")
    else:
        log("Installing Context7...")
        if run("claude plugin install context7@claude-plugins-official"):
            installed.append("Context7")
        else:
            missing.append("Context7")

    # --- Serena ---
    # Migrate from old MCP-based install to plugin
    if check_mcp("serena") and not check_plugin("serena"):
        log("Migrating Serena from MCP to plugin...")
        run("claude mcp remove --scope user serena")
    if check_plugin("serena"):
        configure_serena()
        installed.append("Serena")
    elif command_exists("uvx"):
        log("Installing Serena...")
        if run("claude plugin install serena@claude-plugins-official"):
            configure_serena()
            installed.append("Serena")
        else:
            missing.append("Serena")
    else:
        missing.append("Serena")

    # --- Beads ---
    if command_exists("bd") and check_plugin("beads"):
        installed.append("Beads")
    elif command_exists("bd"):
        log("Installing Beads plugin...")
        if not check_marketplace("steveyegge/beads"):
            run("claude plugin marketplace add steveyegge/beads")
        if run("claude plugin install beads"):
            installed.append("Beads")
        else:
            missing.append("Beads")
    else:
        missing.append("Beads")

    # --- beads-ui ---
    if command_exists("bdui"):
        installed.append("beads-ui")
    elif command_exists("npm"):
        log("Installing beads-ui...")
        if run("npm i -g beads-ui"):
            installed.append("beads-ui")
        else:
            missing.append("beads-ui")
    else:
        missing.append("beads-ui")

    # --- Agent Mail ---
    if check_mail_installed() and check_mail_mcp():
        installed.append("Agent Mail")
    elif command_exists("uvx") and command_exists("git"):
        log("Installing Agent Mail...")
        if not os.path.isdir(MAIL_DIR):
            run(f"git clone --depth 1 https://github.com/Dicklesworthstone/mcp_agent_mail.git {MAIL_DIR}")
        if os.path.isdir(MAIL_DIR):
            try:
                subprocess.run(
                    "uv venv --python 3.13 && uv sync",
                    shell=True, check=True, cwd=MAIL_DIR,
                    capture_output=True, text=True,
                )
            except subprocess.CalledProcessError:
                pass
            # Generate token if needed
            token = read_mail_token()
            if not token:
                token = generate_mail_token()
                os.makedirs(os.path.dirname(MAIL_TOKEN_FILE), exist_ok=True)
                with open(MAIL_TOKEN_FILE, "w") as f:
                    f.write(token)
                os.chmod(MAIL_TOKEN_FILE, 0o600)
            # Write .env
            with open(os.path.join(MAIL_DIR, ".env"), "w") as f:
                f.write(f"HTTP_PORT={MAIL_PORT}\nHTTP_BEARER_TOKEN={token}\n")
            # Register MCP
            run(
                f'claude mcp add agent-mail http://localhost:{MAIL_PORT}/api/ '
                f'--scope user --transport http '
                f'-H "Authorization: Bearer {token}"'
            )
            if check_mail_installed():
                installed.append("Agent Mail")
                # Start server
                if not mail_server_alive():
                    start_mail_server()
            else:
                missing.append("Agent Mail")
    else:
        missing.append("Agent Mail")

    # --- Claudeman ---
    if check_claudeman_installed():
        installed.append("Claudeman")
        if not claudeman_server_alive():
            start_claudeman()
    elif command_exists("npm") and command_exists("tmux") and command_exists("git"):
        log("Installing Claudeman...")
        ok = True
        if not os.path.isdir(CLAUDEMAN_DIR):
            ok = run(f"git clone --depth 1 https://github.com/Ark0N/Claudeman.git {CLAUDEMAN_DIR}")
        if ok and not os.path.isdir(os.path.join(CLAUDEMAN_DIR, "node_modules")):
            ok = run(f"npm install --prefix {CLAUDEMAN_DIR}")
        if ok and check_claudeman_installed():
            installed.append("Claudeman")
            start_claudeman()
        else:
            missing.append("Claudeman")
    else:
        missing.append("Claudeman")

    # Summary
    log("")
    log("Toolkit auto-setup:")
    if installed:
        log(f"  Ready: {', '.join(installed)}")
    if missing:
        log(f"  Missing: {', '.join(missing)} (run /toolkit-setup to install)")

    # Write marker
    touch_marker()


if __name__ == "__main__":
    main()
