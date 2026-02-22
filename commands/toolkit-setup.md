---
name: toolkit-setup
description: Interactive setup for Claude Code tools — install, reinstall, or add individual tools (Context7, Serena, Beads, beads-ui, BMAD)
argument-hint: "[tool-name]"
---

# Toolkit Setup

Run the interactive toolkit setup script.

## Steps

1. Run `node ${CLAUDE_PLUGIN_ROOT}/scripts/setup.mjs`
2. The script will show currently installed tools and prompt the user to select which to install
3. Display the results to the user

If `$ARGUMENTS` contains a specific tool name, pass it to the script:
`node ${CLAUDE_PLUGIN_ROOT}/scripts/setup.mjs --install $ARGUMENTS`

If `$ARGUMENTS` is "all", install all standard tools non-interactively:
`node ${CLAUDE_PLUGIN_ROOT}/scripts/setup.mjs --non-interactive`
