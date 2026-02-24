---
name: toolkit-mode
description: Set project init mode — normal (full), readonly (registry only), or ignore (skip entirely)
argument-hint: "[normal | readonly | ignore] [--list]"
---

# Toolkit Mode

Control how `/toolkit-init` treats a project via `.git/info/toolkit-mode`.

## Modes

| Mode | Effect |
|------|--------|
| **normal** | Full init — Atlas, Relay, Beads, Agent Mail, Serena, BMAD |
| **readonly** | Atlas registry only (no files written to repo). For reference projects you don't develop in |
| **ignore** | Completely skipped by init scans |

## Behavior

Parse `$ARGUMENTS`:

- **No arguments** — show current mode for the project at `$CWD`
- **`normal`** — remove the mode file (back to default)
- **`readonly`** — set readonly mode
- **`ignore`** — set ignore mode
- **`--list`** — scan current directory for all projects with non-default modes

## Steps

### Show current mode (no args)

1. Check if `.git/` exists in `$CWD` — if not, tell the user it's not a git repo
2. Read `.git/info/toolkit-mode` if it exists, otherwise mode is "normal"
3. Display: "**<project-name>**: <mode>"
4. Briefly explain what the mode means

### Set mode (`normal` / `readonly` / `ignore`)

1. Verify `.git/` exists in `$CWD`
2. If mode is `normal`: remove `.git/info/toolkit-mode` if it exists
3. Otherwise: `mkdir -p .git/info` then write the mode string to `.git/info/toolkit-mode`
4. Confirm: "Set **<project-name>** to **<mode>**"
5. Explain what will happen on next `/toolkit-init`

### List (`--list`)

1. Scan current directory for git repos (up to depth 2)
2. For each repo, read `.git/info/toolkit-mode`
3. Print all projects with their modes. Highlight non-default modes.
4. If all are normal, say "All projects use default (normal) mode."
