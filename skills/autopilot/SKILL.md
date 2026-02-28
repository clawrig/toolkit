---
name: autopilot
description: "Autonomous work loop — discover tasks from Beads and Relay, pick the highest-priority one, work on it, close it, repeat. Designed for Codeman respawn sessions and long-running autonomous work."
---

# Autopilot Work Loop

Work autonomously by discovering and completing tasks from Beads and Relay.

## The Loop

Repeat this cycle until there's nothing left to do or you're told to stop:

### 0. Check BMAD planning state (if applicable)

If the project has a `_bmad/` directory, it uses the BMAD-METHOD for structured planning. Before jumping into implementation, verify that planning artifacts exist in `_bmad-output/`:

1. **PRD** — look for files matching `*prd*` or `*product-requirements*` in `_bmad-output/`
2. **Architecture** — look for `*architecture*` or `*arch*` in `_bmad-output/`
3. **Epics/Stories** — look for `*epic*` or `*stories*` in `_bmad-output/`

If artifacts are missing:
- **No PRD** → suggest running `/bmad-bmm-create-prd` first, then stop
- **No architecture** → suggest running `/bmad-bmm-create-architecture` first, then stop
- **No epics/stories** → suggest running `/bmad-bmm-create-epics-and-stories` first, then stop

If all three exist → proceed to step 1.

If `_bmad/` doesn't exist, this isn't a BMAD project — skip this step entirely.

### 1. Check for handoffs first

```bash
bd list --label relay:handoff --status open
```

Handoffs are high-priority — another session saved context specifically for continuation. If any exist, pick the most recent one and restore its context:

```bash
bd show <handoff-id>
bd update <handoff-id> --status in_progress
```

Read the handoff description carefully. It contains: objective, branch, summary of what was done, decisions made, next steps, active issues, and blockers. **Resume from where they left off.**

If the handoff specifies a branch, verify you're on it:

```bash
git branch --show-current
```

### 2. Find ready tasks

If no handoffs, check for unblocked work:

```bash
bd ready
```

This lists tasks with no blockers, sorted by priority. Pick the highest-priority task.

If `bd ready` returns nothing, check if there are blocked tasks that might be unblockable:

```bash
bd list --status open
```

### 3. Start working on the task

```bash
bd update <issue-id> --status in_progress
```

Read the issue details to understand what needs to be done:

```bash
bd show <issue-id>
```

### 4. Multi-agent check (if Agent Mail is available)

If other agents might be working on this project, coordinate:

- Check inbox for messages from other agents: `fetch_inbox(...)`
- Reserve files you plan to edit: `file_reservation_paths(..., reason="<issue-id>")`
- Announce your work: `send_message(..., thread_id="<issue-id>")`

Skip this step if you're the only agent working on the project.

### 5. Do the work

Implement what the task describes. Follow standard practices:
- Read relevant code before modifying
- Run tests after changes
- Commit with the issue ID in the message (e.g., `[bd-123] Fix auth timeout`)

**BMAD projects:** If the task matches a BMAD story (check `_bmad-output/` for story files), use `/bmad-bmm-dev-story` to implement it — this follows the structured dev workflow with acceptance criteria and checklist tracking.

### 6. Close and loop

For non-trivial changes in BMAD projects, run `/bmad-bmm-code-review` before closing the task. This checks the implementation against architecture decisions and coding standards defined during planning.

```bash
bd close <issue-id>
```

If you reserved files, release them:

```
release_file_reservations(project_key="<path>", agent_name="<your name>")
```

**Go back to step 1.** Pick the next task and continue.

## When to stop

- `bd ready` returns no tasks AND no handoffs exist
- You encounter a blocker you can't resolve — create a new issue describing the blocker, then move on to the next task
- You've been explicitly told to stop

## When something goes wrong

- **Test failures:** Fix them before closing the task. If you can't fix them, leave the task in_progress and add a comment: `bd comment <id> "Tests failing: <details>"`
- **Merge conflicts:** Resolve them. If too complex, leave a comment and move to the next task.
- **Missing context:** Read related issues (`bd show`), check git log, search the codebase. Don't guess — investigate.
- **Blocked by another task:** Mark the dependency: `bd dep add <this-id> --blocked-by <other-id>`, then move to the next task.

## Codeman integration

When running in a Codeman-managed session, use this as the respawn update prompt:

```
Check for relay handoffs and beads ready tasks, then work on the highest priority one. Run /toolkit:autopilot for the full protocol.
```

This ensures each respawn cycle picks up real work instead of wandering.
