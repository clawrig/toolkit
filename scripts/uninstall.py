#!/usr/bin/env python3
"""Claude Toolkit Uninstall — remove installed tools. Stdlib only."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import (
    BOLD, DIM, GREEN, RESET,
    check_mcp, check_plugin, command_exists, log, run,
)

# ── Tool definitions (uninstall only) ─────────────────────────────────────────

TOOLS = {
    "atlas": {
        "name": "Atlas",
        "check": lambda: check_plugin("atlas"),
        "uninstall": lambda: run("claude plugin uninstall famdeck-atlas"),
        "note": "Per-project .claude/atlas.yaml files and ~/.claude/atlas/ registry are preserved.",
    },
    "relay": {
        "name": "Relay",
        "check": lambda: check_plugin("relay"),
        "uninstall": lambda: run("claude plugin uninstall famdeck-relay"),
        "note": "Per-project .claude/relay.yaml files are preserved.",
    },
    "context7": {
        "name": "Context7",
        "check": lambda: check_mcp("context7"),
        "uninstall": lambda: run("claude mcp remove --scope user context7"),
    },
    "serena": {
        "name": "Serena",
        "check": lambda: check_mcp("serena"),
        "uninstall": lambda: run("claude mcp remove --scope user serena"),
    },
    "beads": {
        "name": "Beads (plugin)",
        "check": lambda: check_plugin("beads"),
        "uninstall": lambda: (
            run("claude plugin uninstall beads"),
            run("claude plugin marketplace remove beads-marketplace"),
        ),
        "note": "The bd CLI is not removed. Uninstall it separately.",
    },
    "beadsui": {
        "name": "beads-ui",
        "check": lambda: command_exists("bdui"),
        "uninstall": lambda: run("npm uninstall -g beads-ui"),
    },
    "mail": {
        "name": "Agent Mail",
        "check": lambda: check_mcp("agent-mail"),
        "uninstall": lambda: run("claude mcp remove --scope user agent-mail"),
        "note": "Server repo at ~/.mcp_agent_mail/ not removed. Delete manually if needed.",
    },
    "bmad": {
        "name": "BMAD-METHOD",
        "check": lambda: os.path.isdir(os.path.join(os.getcwd(), "_bmad")),
        "uninstall": lambda: subprocess.run("npx bmad-method uninstall", shell=True).returncode == 0,
        "note": "BMAD is per-project. Run this from the project directory.",
    },
}

# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    log()
    log(f"  {BOLD}Claude Toolkit Uninstall{RESET}")
    log(f"  {'=' * 24}")
    log()

    if not command_exists("claude"):
        log("Error: `claude` CLI not found.")
        sys.exit(1)

    log("Checking installed tools...")
    log()

    installed = []
    for id_, t in TOOLS.items():
        try:
            found = t["check"]()
        except Exception:
            found = False

        icon = f"{GREEN}✓{RESET}" if found else f"{DIM}·{RESET}"
        log(f"  {icon} {id_:<10} {t['name']}")
        if found:
            installed.append(id_)

    log()

    if not installed:
        log("Nothing to uninstall.")
        return

    log(f"Installed: {', '.join(installed)}")
    try:
        answer = input('Remove (space-separated IDs, "all", or "q" to quit): ').strip().lower()
    except (EOFError, KeyboardInterrupt):
        log("\nCancelled.")
        sys.exit(0)

    if not answer or answer == "q":
        log("Cancelled.")
        sys.exit(0)

    selected = installed if answer == "all" else answer.split()

    for id_ in selected:
        t = TOOLS.get(id_)
        if not t:
            log(f"\nUnknown tool: {id_}")
            continue

        log(f"\nRemoving {t['name']}...")
        t["uninstall"]()
        log(f"✓ {t['name']} removed")
        if t.get("note"):
            log(f"  Note: {t['note']}")

    log()
    log(f"  {BOLD}Uninstall complete!{RESET}")
    log("  Restart Claude Code for changes to take effect.")
    log()


if __name__ == "__main__":
    main()
