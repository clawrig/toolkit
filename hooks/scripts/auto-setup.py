#!/usr/bin/env python3
"""SessionStart hook — check tool status, start servers. No installs (claude CLI hangs in-session)."""

import os
import sys

# Add scripts/ to path so we can import lib
scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(scripts_dir))

from lib import (
    CODEMAN_PORT, DOLT_PORT, MAIL_PORT,
    check_codeman_installed, check_dolt_installed, check_mail_installed,
    check_mail_mcp, check_plugin, codeman_server_alive, command_exists,
    dolt_server_alive, log, mail_server_alive, marker_is_fresh,
    start_codeman, start_dolt_server, start_mail_server, touch_marker,
)


def main():
    # Always ensure mail server is running (if installed)
    if check_mail_installed() and not mail_server_alive():
        if start_mail_server():
            log("Toolkit: Agent Mail server started")

    # Always ensure Dolt sql-server is running (if installed)
    if check_dolt_installed() and not dolt_server_alive():
        if start_dolt_server():
            log("Toolkit: Dolt sql-server started")

    # Always ensure Codeman is running (if installed)
    if check_codeman_installed() and not codeman_server_alive():
        if start_codeman():
            log("Toolkit: Codeman server started")

    # Skip status check if marker is fresh
    if marker_is_fresh():
        return

    # Check what's installed vs missing (read-only, no claude CLI calls)
    missing = []

    if not check_plugin("atlas"):
        missing.append("Atlas")
    if not check_plugin("relay"):
        missing.append("Relay")
    if not check_plugin("context7"):
        missing.append("Context7")
    if not check_plugin("serena"):
        missing.append("Serena")
    if not check_dolt_installed():
        missing.append("Dolt (brew install dolt)")
    if not (command_exists("bd") and check_plugin("beads")):
        missing.append("Beads")
    if not command_exists("bdui"):
        missing.append("beads-ui")
    if not (check_mail_installed() and check_mail_mcp()):
        missing.append("Agent Mail")
    if not check_codeman_installed():
        missing.append("Codeman")

    if missing:
        log(f"Toolkit: missing tools: {', '.join(missing)}")
        log("  Run in terminal: python3 ~/.claude/plugins/cache/ivintik/famdeck-toolkit/*/scripts/setup.py")

    touch_marker()


if __name__ == "__main__":
    main()
