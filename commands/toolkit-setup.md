---
name: toolkit-setup
description: Interactive setup for Claude Code tools — install, reinstall, or add individual tools
argument-hint: "[tool-name]"
---

# Toolkit Setup

Run the interactive toolkit setup script.

## Steps

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py`
2. The script will show currently installed tools and prompt the user to select which to install
3. Display the results to the user

If `$ARGUMENTS` contains a specific tool name, pass it to the script:
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py --install $ARGUMENTS`

If `$ARGUMENTS` is "all", install all standard tools non-interactively:
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py --non-interactive`
