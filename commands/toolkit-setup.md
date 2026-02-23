---
name: toolkit-setup
description: Interactive setup for Claude Code tools — install, reinstall, or add individual tools
argument-hint: "[tool-name]"
---

# Toolkit Setup

The setup script must run from a **regular terminal** (outside Claude Code) because `claude plugin install` and `claude mcp add` hang when invoked from within a running session.

Do NOT attempt to run the script yourself. Instead, tell the user to run one of these commands in their terminal:

**Install interactively:**
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py
```

**Install a specific tool** (if `$ARGUMENTS` contains a tool name):
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py --install $ARGUMENTS
```

**Install all standard tools** (if `$ARGUMENTS` is "all"):
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py --non-interactive
```

Present the command clearly so the user can copy-paste it. Use `/toolkit:toolkit-status` to show current status (that one works inside Claude Code).
