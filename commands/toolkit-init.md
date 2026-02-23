---
name: toolkit-init
description: Initialize current project for ClawRig ecosystem — Atlas, Relay, Serena, BMAD
argument-hint: "[--atlas-only | --relay-only | --no-bmad]"
---

# Project Init

Initialize the current project for the ClawRig ecosystem.

## Steps

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init.py`
2. The script will:
   - Register the project in Atlas (if atlas plugin is installed)
   - Configure Relay trackers based on the git remote (if relay plugin is installed)
   - Initialize Beads issue tracker — `bd init` (if bd CLI is available and project is a git repo)
   - Install Agent Mail pre-commit guard (if Agent Mail is installed and server is running)
   - Generate `.serena/project.yml` with auto-detected languages (if serena plugin is installed)
   - Install BMAD workflow framework (unless `--no-bmad` flag is passed)
3. Display the results to the user
4. **After init completes**, trigger Serena onboarding if `.serena/project.yml` was just created:
   - Use the `onboarding` MCP tool from Serena to discover project structure and build/test tasks
   - This stores results in `.serena/memories/` for future sessions

If `$ARGUMENTS` contains flags, pass them through:
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init.py $ARGUMENTS`

For non-interactive use (e.g., from CI or scripts):
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init.py --non-interactive`
