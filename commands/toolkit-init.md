---
name: toolkit-init
description: Scan subdirectories for git repos and initialize each for ClawRig ecosystem — Atlas, Relay, Beads, Serena, Agent Mail
argument-hint: "[--depth=N] [--atlas-only | --relay-only | --no-bmad | --non-interactive]"
---

# Batch Project Init

Scan the current directory for git repositories and initialize each one for the ClawRig ecosystem.

## Steps

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init.py`
2. The script will:
   - Scan subdirectories (default depth=2) for `.git/` directories
   - For each repo found, initialize: Atlas registration, Relay tracker config, Beads, Agent Mail guard, Serena project config
   - Skip repos that are already initialized
   - Print a summary table of results
3. Display the results to the user

If `$ARGUMENTS` contains flags, pass them through:
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init.py $ARGUMENTS`

## Options

- `--depth=N` — How deep to scan for git repos (default: 2)
- `--atlas-only` — Only register projects in Atlas
- `--relay-only` — Only configure Relay trackers
- `--no-bmad` — Skip BMAD installation
- `--non-interactive` — No prompts, use defaults for everything
