---
name: toolkit-ignore
description: Exclude current project from toolkit-init scans, or list/remove ignores
argument-hint: "[--list | --remove | path]"
---

# Toolkit Ignore

Manage the `.git/info/toolkit-ignore` marker that excludes projects from `/toolkit-init` scans.

## Behavior

Parse `$ARGUMENTS`:

- **No arguments** — ignore the current project (`$CWD`)
- **A path** — ignore the project at that path
- `--list` — list all ignored projects under current directory (scan for the marker)
- `--remove` — remove the ignore marker from the current project (or given path)

## Steps

### Ignore (default / path)

1. Resolve the target directory (argument or `$CWD`)
2. Verify `.git/` exists in the target — if not, tell the user it's not a git repo
3. Create `.git/info/` if missing: `mkdir -p <target>/.git/info`
4. Create the marker: `touch <target>/.git/info/toolkit-ignore`
5. Confirm: "Ignored **<project-name>** — `/toolkit-init` will skip this project."

### Remove (`--remove`)

1. Resolve the target directory (second argument or `$CWD`)
2. Check if `.git/info/toolkit-ignore` exists — if not, tell the user it's not ignored
3. Remove: `rm <target>/.git/info/toolkit-ignore`
4. Confirm: "Unignored **<project-name>** — `/toolkit-init` will include this project."

### List (`--list`)

1. Scan current directory for git repos (like init does, up to depth 2)
2. For each repo, check if `.git/info/toolkit-ignore` exists
3. Print ignored projects. If none found, say "No ignored projects found."
