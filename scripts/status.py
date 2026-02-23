#!/usr/bin/env python3
"""Toolkit status — show installed tools and per-project state."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import (
    BOLD, CYAN, DIM, GREEN, RESET, YELLOW,
    check_mail_installed, check_mail_mcp,
    check_mcp, check_plugin, command_exists, log, marker_mtime_str,
)

HOME = os.path.expanduser("~")
CWD = os.getcwd()


def main():
    log()
    log(f"  {BOLD}Toolkit Status{RESET}")
    log(f"  {'=' * 14}")
    log()

    # ── User-level tools ──────────────────────────────────────────────────

    tools = [
        ("context7", "Context7", "Up-to-date library docs (plugin)",
         lambda: check_plugin("context7"), False),
        ("serena", "Serena", "Semantic code navigation via LSP",
         lambda: check_plugin("serena"), False),
        ("beads", "Beads", "Git-backed issue tracker + plugin",
         lambda: command_exists("bd") and check_plugin("beads"), False),
        ("beadsui", "beads-ui", "Browser UI for Beads",
         lambda: command_exists("bdui"), False),
        ("mail", "Agent Mail", "Cross-project agent messaging",
         lambda: check_mail_installed() and check_mail_mcp(), False),
        ("bmad", "BMAD-METHOD", "SDLC workflow framework",
         lambda: os.path.isdir(os.path.join(CWD, "_bmad")), True),
    ]

    for id_, name, desc, check_fn, optional in tools:
        try:
            installed = check_fn()
        except Exception:
            installed = False
        icon = f"{GREEN}✓{RESET}" if installed else f"{DIM}·{RESET}"
        opt = f" {DIM}[optional]{RESET}" if optional else ""
        log(f"  {icon} {id_:<12} {name} — {desc}{opt}")

    # ── Per-project state ─────────────────────────────────────────────────

    project_name = os.path.basename(os.path.abspath(CWD))
    atlas_config = os.path.join(CWD, ".claude", "atlas.yaml")
    relay_config = os.path.join(CWD, ".claude", "relay.yaml")
    beads_dir = os.path.join(CWD, ".beads")
    serena_config = os.path.join(CWD, ".serena", "project.yml")

    has_atlas = os.path.isfile(atlas_config)
    has_relay = os.path.isfile(relay_config)
    has_beads = os.path.isdir(beads_dir)
    has_serena = os.path.isfile(serena_config)

    if has_atlas or has_relay or has_beads or has_serena or check_plugin("atlas") or check_plugin("relay") or check_plugin("serena"):
        log()
        log(f"  {BOLD}Project:{RESET} {project_name}")

        if has_atlas:
            # Try to extract name from atlas.yaml
            try:
                content = open(atlas_config).read()
                import re
                m = re.search(r'^name:\s*(.+)$', content, re.M)
                aname = m.group(1).strip().strip('"').strip("'") if m else project_name
            except OSError:
                aname = project_name
            log(f"  {GREEN}✓{RESET} {'atlas':<12} Registered as \"{aname}\"")
        elif check_plugin("atlas"):
            log(f"  {DIM}·{RESET} {'atlas':<12} No .claude/atlas.yaml found")

        if has_relay:
            log(f"  {GREEN}✓{RESET} {'relay':<12} .claude/relay.yaml configured")
        elif check_plugin("relay"):
            log(f"  {DIM}·{RESET} {'relay':<12} No .claude/relay.yaml found")

        if has_beads:
            log(f"  {GREEN}✓{RESET} {'beads':<12} .beads/ initialized")
        elif command_exists("bd"):
            log(f"  {DIM}·{RESET} {'beads':<12} No .beads/ found (run /toolkit-init)")

        # Check Agent Mail guard
        pre_commit = os.path.join(CWD, ".git", "hooks", "pre-commit")
        has_guard = False
        if os.path.isfile(pre_commit):
            try:
                has_guard = "agent" in open(pre_commit).read().lower()
            except OSError:
                pass
        if has_guard:
            log(f"  {GREEN}✓{RESET} {'mail-guard':<12} Pre-commit guard installed")
        elif check_mail_installed():
            log(f"  {DIM}·{RESET} {'mail-guard':<12} No pre-commit guard (run /toolkit-init)")

        if has_serena:
            log(f"  {GREEN}✓{RESET} {'serena':<12} .serena/project.yml configured")
        elif check_plugin("serena"):
            log(f"  {DIM}·{RESET} {'serena':<12} No .serena/project.yml found (run /toolkit-init)")

    # ── Marker info ───────────────────────────────────────────────────────

    log()
    mtime = marker_mtime_str()
    if mtime:
        log(f"  Last auto-setup: {mtime}")
    else:
        log(f"  Auto-setup has not run yet")
    log()


if __name__ == "__main__":
    main()
