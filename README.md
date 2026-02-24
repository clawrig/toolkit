# ClawRig Toolkit

Setup, project initialization, and service management for the ClawRig ecosystem — a set of Claude Code plugins that add project awareness, issue routing, handoffs, multi-agent coordination, and code navigation to your sessions.

## What's Included

The toolkit installs and manages these tools:

| Tool | What it does | Type |
|------|-------------|------|
| **Atlas** | Global project registry, cross-project awareness, project metadata | Plugin |
| **Relay** | Issue routing (GitHub/GitLab/Jira/Beads), handoffs, cross-project messaging | Plugin |
| **Context7** | Up-to-date library docs via MCP plugin | Plugin |
| **Serena** | Semantic code navigation via LSP — definitions, references, rename across 30+ languages | Plugin |
| **Beads** | Git-backed issue tracker in your repo (`.beads/`). 30+ slash commands for issues, epics, dependencies | CLI + plugin |
| **beads-ui** | Browser-based kanban board, epic view, and search for Beads issues | Global CLI |
| **Agent Mail** | Multi-agent coordination — identities, messaging, file reservations, pre-commit guard | HTTP server + MCP |
| **Claudeman** | Persistent autonomous Claude sessions — respawn controller, tmux persistence, multi-session dashboard | Web service |
| **BMAD-METHOD** | SDLC workflow framework with PM, Architect, Dev, QA personas | Per-project |

## Quick Start

### 1. Install the plugin

```bash
claude plugin install /path/to/clawrig-toolkit
```

### 2. Run setup

Inside Claude Code:

```
/toolkit-setup
```

This shows what's installed, what's missing, and lets you pick which tools to install. To install everything at once:

```
/toolkit-setup all
```

### 3. Restart Claude Code

Plugins and MCP servers connect on startup. Restart after first install.

### 4. Initialize a project

Navigate to a project directory and run:

```
/toolkit-init
```

This runs the full per-project initialization sequence:

1. **Atlas** — registers the project in the global registry, creates `.claude/atlas.yaml`
2. **Relay** — auto-configures issue trackers based on git remote (GitHub/GitLab/Beads)
3. **Beads** — initializes `.beads/` issue database (`bd init`)
4. **Agent Mail** — installs the pre-commit guard (blocks conflicting file edits between agents)
5. **Serena** — generates `.serena/project.yml` with auto-detected languages, then runs onboarding
6. **BMAD** — installs SDLC workflow templates

## Commands

| Command | Description |
|---------|-------------|
| `/toolkit-setup [tool]` | Install tools — interactive or by name |
| `/toolkit-status` | Show installation status of all tools + per-project state |
| `/toolkit-init [flags]` | Initialize current project (full sequence above) |
| `/toolkit-uninstall [tool\|all]` | Remove installed tools |

### Skills

| Skill | Description |
|-------|-------------|
| `/toolkit:autopilot` | Autonomous work loop — discover tasks from Beads/Relay, work on them, close, repeat. For Claudeman respawn and long-running sessions |
| `/toolkit:coordination` | Multi-agent coordination protocol — session bootstrap, file reservations, threaded messaging, Beads integration |

### toolkit-init flags

| Flag | Effect |
|------|--------|
| `--atlas-only` | Only register in Atlas |
| `--relay-only` | Only configure Relay trackers |
| `--no-bmad` | Skip BMAD installation |
| `--non-interactive` | Skip prompts, use auto-detected defaults |

Beads, Agent Mail guard, and Serena always run (if their tools are installed). Use `--atlas-only` or `--relay-only` to limit scope.

## Auto-Setup

The toolkit runs a SessionStart hook that:

1. **Starts services** — Agent Mail (port 8765) and Claudeman (port 3000) if installed but not running
2. **Installs missing tools** — non-interactively, with a 7-day cooldown
3. **Migrates legacy installs** — Context7 and Serena are auto-migrated from raw MCP to plugin

This means tools stay available across sessions without manual intervention.

## Tool Reference

### Atlas

Maintains a central registry of all your projects at `~/.claude/atlas/registry.yaml`. Each project can have a `.claude/atlas.yaml` with metadata (name, summary, tags, links, docs). Atlas provides the project context that other tools build on.

**Key commands:**

```
/atlas:projects        # List registered projects
/atlas:docs            # Show project documentation links
/atlas:context         # Display current project context
```

**Per-project setup:** `/toolkit-init` creates `.claude/atlas.yaml` with auto-detected name, tags, and summary, and registers the project in the global registry.

**Installed from:** `ivintik` marketplace
**Docs:** https://github.com/clawrig/atlas

### Relay

Routes issues to the right tracker, manages work handoffs within a project, and sends messages between projects via Agent Mail.

**Key commands:**

```
/relay:issue <title>   # Create an issue (routed by config)
/relay:handoff         # Save work context as a beads issue for another session to pick up
/relay:pickup          # Resume a handed-off task
/relay:status          # Show tracker status across configured sources
/relay:trackers        # View/manage per-project tracker configuration
```

**Per-project setup:** `/toolkit-init` creates `.claude/relay.yaml` with auto-detected issue trackers from the git remote (GitHub/GitLab) plus Beads if available.

**Installed from:** `ivintik` marketplace
**Docs:** https://github.com/clawrig/relay

### Context7

Provides up-to-date documentation for libraries directly in your Claude Code session. When Claude needs to look up API docs, it queries Context7 instead of relying on training data.

**Usage:** Automatic — Claude uses it when it needs library documentation.

**Installed from:** `claude-plugins-official` marketplace
**Docs:** https://context7.com

### Serena

Language Server Protocol (LSP) integration that gives Claude semantic understanding of your code: jump to definitions, find all references, rename symbols, and get symbol overviews across 30+ languages.

**Usage:** Available as MCP tools — Claude uses them automatically when navigating code.

**Per-project setup:** `/toolkit-init` generates `.serena/project.yml` with auto-detected languages (TypeScript, Python, Rust, Go, Java, Scala, Ruby, PHP, Swift, C++, Elixir, Dart). After init, Serena onboarding runs to discover the project structure and build/test tasks, storing results in `.serena/memories/`.

**Installed from:** `claude-plugins-official` marketplace
**Docs:** https://github.com/oraios/serena

### Beads

A git-native issue tracker. Issues live in `.beads/` inside your repo, committed alongside code. Branch-scoped, merge-friendly, works offline.

**Per-project setup:** `/toolkit-init` runs `bd init` to create `.beads/` with the database, config, and git hooks. The issue prefix is auto-derived from the project name.

**Key commands:**

```
/beads:create          # Create a new issue
/beads:list            # List issues with filters
/beads:show <id>       # Show issue details
/beads:update <id>     # Update status, priority, fields
/beads:close <id>      # Close a completed issue
/beads:ready           # Find tasks with no blockers
/beads:epic            # Manage epics
/beads:dep             # Manage dependencies between issues
/beads:search <query>  # Full-text search
/beads:workflow        # AI-supervised issue workflow guide
```

**Docs:** https://github.com/steveyegge/beads

### beads-ui

Opens a browser UI for your Beads issues — kanban board, epic view, search, and filtering. No config needed — it reads from `.beads/` directly.

**Usage:**

```bash
bdui                   # Launch in current project
```

**Docs:** https://www.npmjs.com/package/beads-ui

### Agent Mail

Mail-like coordination layer for multi-agent workflows. Provides memorable agent identities (adjective+noun names like "GreenCastle"), inbox/outbox messaging, file reservation leases, threaded conversations, and a pre-commit guard. All backed by Git (human-auditable) and SQLite (fast search with FTS5).

**Key features:**
- **File reservations** — advisory locks on files before editing, with enforcement via pre-commit guard
- **Threaded messaging** — agents announce work, share progress, coordinate file ownership
- **Beads integration** — use issue IDs (`bd-123`) as thread IDs for unified tracking
- **Web UI** — browse at `http://localhost:8765/mail` for inbox, threads, reservations
- **Human Overseer** — send high-priority messages to agents from the web UI
- **Contact policies** — control who can message whom (open, auto, contacts_only, block_all)
- **Cross-project** — link repos under a product for cross-project search and inbox

**Per-project setup:** `/toolkit-init` installs the pre-commit guard, which blocks commits touching files exclusively reserved by another agent.

**Details:**
- Runs on `http://localhost:8765`
- Data stored in `~/.mcp_agent_mail/`
- Auth via bearer token (auto-generated during setup)
- Auto-started by the toolkit's SessionStart hook

**Usage:** See `/toolkit:coordination` skill for the full multi-agent workflow.

**Docs:** https://github.com/Dicklesworthstone/mcp_agent_mail

### Claudeman

Web-based session manager that turns Claude Code into a persistent autonomous agent. Sessions run inside tmux and survive network drops, machine sleep, and server restarts. The respawn controller detects idle Claude and automatically sends continuation prompts, keeping work going unattended for 24+ hours.

**Key features:**
- **Respawn Controller** — state machine that detects idle Claude, sends continuation prompts, auto-compacts context at token thresholds, and refreshes sessions when context fills up
- **Tmux persistence** — sessions survive anything (SSH disconnects, VPN drops, machine sleep)
- **Multi-session dashboard** — monitor multiple parallel Claude sessions with real-time terminal rendering
- **Background agent visualization** — draggable floating windows showing Task tool agents with connection graphs
- **Desktop notifications** — alerts when Claude needs tool approval (red) or goes idle (yellow)
- **Zero-latency typing** — Mosh-inspired local echo for smooth remote access over SSH
- **Token tracking** — per-session token count and cost estimates

**Respawn configuration:**
```json
{
  "respawn": {
    "enabled": true,
    "durationMinutes": 480,
    "updatePrompt": "Check for relay handoffs and beads ready tasks, then work on the highest priority one. Run /toolkit:autopilot for the full protocol.",
    "idleTimeoutMs": 5000
  },
  "autoCompact": { "thresholdTokens": 110000 },
  "autoFresh": { "thresholdTokens": 140000 }
}
```

**Details:**
- Dashboard at `http://localhost:3000`
- Installed at `~/.claudeman/`
- Requires tmux and Node.js 18+
- Auto-started by the toolkit's SessionStart hook
- Creates new Claude sessions (does not attach to existing ones)
- Can also start via `claudeman web` CLI

**Docs:** https://github.com/Ark0N/Claudeman

### BMAD-METHOD

Structured SDLC workflow framework with personas (PM, Architect, Developer, QA). Guides projects through four phases: Analysis → Planning → Solutioning → Implementation. Per-project — installs a `_bmad/` directory with workflow templates and outputs planning artifacts to `_bmad-output/`.

**Phases:**

1. **Analysis** — gather requirements, define problem space
2. **Planning** — create PRD, define scope and priorities
3. **Solutioning** — design architecture, break into epics and stories
4. **Implementation** — develop stories, review code, validate against plan

**Key commands:**

| Command | Phase | What it does |
|---------|-------|-------------|
| `/bmad-bmm-create-prd` | Planning | Create Product Requirements Document |
| `/bmad-bmm-create-architecture` | Solutioning | Design technical architecture |
| `/bmad-bmm-create-epics-and-stories` | Solutioning | Break architecture into implementable units |
| `/bmad-bmm-create-next-story` | Solutioning | Generate the next story from epics |
| `/bmad-bmm-dev-story` | Implementation | Implement a story with checklist tracking |
| `/bmad-bmm-code-review` | Implementation | Review code against architecture and standards |
| `/bmad-bmm-correct-course` | Any | Re-evaluate and adjust plan mid-flight |
| `/bmad-bmm-yolo` | Implementation | Quick implementation mode (skip ceremony) |

**Output:** All planning artifacts (PRD, architecture docs, epic/story files) are written to `_bmad-output/` in the project root.

**Per-project setup:** Installed automatically by `/toolkit-init`. In non-interactive mode, installs with `--modules bmm --tools claude-code --yes`. Skip with `--no-bmad`.

**Docs:** https://www.npmjs.com/package/bmad-method

## Workflows

### Starting a new project

```
cd ~/dev/my-new-project
git init && git remote add origin git@github.com:me/my-new-project.git

# In Claude Code:
/toolkit-init
```

This runs the full init sequence: Atlas registration, Relay tracker config (GitHub + Beads), Beads init, Agent Mail guard, Serena setup + onboarding, and BMAD install. Everything auto-detected from your git remote and project files.

### Daily work on an existing project

```
cd ~/dev/my-project

# Claude Code starts → toolkit auto-starts Agent Mail and Claudeman
# → Atlas detects the current project
# → Relay loads tracker config

# Create issues as you find them:
/relay:issue "Fix login timeout on slow networks"

# Track work locally:
/beads:create
# ... work on the issue ...
/beads:close <id>

# Check what's ready to work on:
/beads:ready
```

### Handing off work between sessions

When you need to stop but want another session (or another person) to continue:

```
# Save your current context:
/relay:handoff

# This creates a beads issue with the relay:handoff label,
# capturing what you were doing, what's left, and relevant files.
```

In the next session (same project, same branch):

```
# See what handoffs are waiting:
/relay:pickup --list

# Resume one:
/relay:pickup
```

### Autonomous overnight work (Claudeman)

Let Claude work on a project unattended:

```
# Open Claudeman dashboard:
# http://localhost:3000

# 1. Create a new session via the UI
# 2. Seed the project with tasks:
#    /beads:create (repeat for each task)
#    /relay:handoff (if continuing existing work)
# 3. Give Claude an initial prompt:
#    "Run /toolkit:autopilot — work through all ready tasks"
# 4. Enable respawn (8 hours) with this update prompt:
#    "Check for relay handoffs and beads ready tasks, then work on
#     the highest priority one. Run /toolkit:autopilot for the full protocol."
# 5. Walk away — Claude picks tasks from the queue, works, closes,
#    picks next. Auto-compacts at 110k tokens, auto-refreshes at 140k.
# 6. Check dashboard in the morning for progress
```

The autopilot loop means each respawn cycle picks real work from Beads instead of wandering. Create enough tasks beforehand so Claude has a clear queue.

Desktop notifications alert you if Claude needs tool approval — click the notification to jump directly to the session.

**Manual tmux access** (for debugging or if the web UI is down):
```bash
tmux ls                              # See all Claudeman sessions
tmux attach-session -t claudeman-myproject  # Observe directly
```

### Running parallel sessions

```
# Create multiple sessions in Claudeman dashboard:
# Session 1: "Implement user authentication" (project A)
# Session 2: "Write integration tests" (project B)
# Session 3: "Refactor database layer" (project A)

# Each runs independently in its own tmux window.
# Dashboard shows all sessions with progress indicators.
# Notifications fire for any session needing attention.
```

When sessions work on the same project, use Agent Mail coordination (`/toolkit:coordination`) to prevent file conflicts.

### Multi-agent coordination

When multiple agents work on the same project (e.g., via Claudeman/tmux sessions):

```
# The coordination skill teaches Claude the full protocol:
/toolkit:coordination
```

**The protocol in brief:**

1. **Start session** — `macro_start_session(...)` registers your identity, checks inbox
2. **Reserve files** — `file_reservation_paths(...)` signals which files you'll edit
3. **Announce** — `send_message(...)` in a thread tied to the beads issue ID
4. **Work** — edit files, reply in thread with progress updates
5. **Check inbox** — `fetch_inbox(...)` periodically for messages from other agents
6. **Release** — `release_file_reservations(...)` when done
7. **Announce completion** — final message in the thread

The pre-commit guard (installed by `/toolkit-init`) blocks commits that touch files exclusively reserved by another agent. Bypass in emergencies with `AGENT_MAIL_BYPASS=1 git commit`.

### Multi-project workflow

When working across multiple projects that need to coordinate:

```
# Check what projects are registered:
/atlas:projects

# Agent Mail supports cross-project messaging.
# Use request_contact / respond_contact to establish
# communication between agents in different projects.

# Or link repos under a product for unified inbox:
# ensure_product → products_link → fetch_inbox_product
```

### BMAD greenfield project

Full lifecycle from init through planning to implementation:

```
cd ~/dev/my-new-project
git init

# In Claude Code:
/toolkit-init

# BMAD installs _bmad/ — now follow the phases:

# 1. Planning — create the PRD
/bmad-bmm-create-prd

# 2. Solutioning — design architecture
/bmad-bmm-create-architecture

# 3. Solutioning — break into stories
/bmad-bmm-create-epics-and-stories

# 4. Implementation — work through stories
/toolkit:autopilot
# Autopilot checks _bmad-output/ for planning artifacts,
# then uses /bmad-bmm-dev-story for each matching task
```

### BMAD + Beads bridge

Create Beads issues from BMAD stories for dependency tracking and multi-session persistence:

```
# After /bmad-bmm-create-epics-and-stories produces story files:
# Read each story from _bmad-output/ and create a Beads issue:
/beads:create
# Copy the story title, acceptance criteria, and reference
# the BMAD story file in the description.

# Now autopilot picks stories via bd ready,
# and /bmad-bmm-dev-story handles the implementation details.
```

This gives you the best of both: BMAD's structured planning with Beads' dependency graphs, status tracking, and cross-session persistence.

### BMAD + Claudeman

Seed planning first, then let autopilot work through stories overnight:

```
# 1. Do planning interactively (phases 1-3):
/bmad-bmm-create-prd
/bmad-bmm-create-architecture
/bmad-bmm-create-epics-and-stories

# 2. Create Beads issues from stories (optional but recommended)
# 3. Launch a Claudeman session with respawn enabled
# 4. Initial prompt: "Run /toolkit:autopilot"
# 5. Autopilot sees _bmad-output/ artifacts exist →
#    proceeds to pick tasks and implement with /bmad-bmm-dev-story
```

Without planning artifacts, autopilot will stop and suggest running the planning commands first — preventing Claudeman from jumping into code prematurely.

### BMAD + multi-agent

Distribute BMAD personas across agents for parallel planning and implementation:

```
# Agent 1 (PM): Creates PRD
#   → Reserves _bmad-output/**, runs /bmad-bmm-create-prd
#   → Releases reservation, announces "PRD ready" via Agent Mail

# Agent 2 (Architect): Waits for PRD, then creates architecture
#   → Reserves _bmad-output/**, runs /bmad-bmm-create-architecture
#   → Then /bmad-bmm-create-epics-and-stories
#   → Releases, announces "stories ready"

# Agents 3-N (Devs): Wait for stories, then implement in parallel
#   → Each picks a different story via bd ready
#   → Reserves source files (not _bmad-output/)
#   → Runs /bmad-bmm-dev-story, then /bmad-bmm-code-review
```

See `/toolkit:coordination` for the full Agent Mail protocol including file reservations and BMAD persona distribution.

### Checking toolkit health

```
/toolkit-status
```

Shows:
- **User-level tools** — installed/missing for each tool
- **Per-project state** — Atlas registration, Relay config, Beads init, Agent Mail guard, Serena config
- **Auto-setup marker** — when the last auto-install ran

### Adding a tool you skipped earlier

```
/toolkit-setup serena
```

Installs just that one tool. Or run `/toolkit-setup` with no arguments for the interactive picker.

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                        TOOLKIT (this plugin)                          │
│  Setup, auto-install, project init, coordination skill                │
└──────────────────┬────────────────────────────────────────────────────┘
                   │ installs & manages
                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Atlas │ Relay │ Context7 │ Serena │ Beads │ beads-ui │ Agent Mail │  │
│(plug) │(plug) │ (plugin) │(plugin)│(CLI+P)│  (CLI)   │ (HTTP+MCP) │  │
│       │       │          │        │       │          │            │  │
│ ┌─────┴───────┘          │        │       │          │ Claudeman  │  │
│ │ Cross-project          │        │       │          │   (Web)    │  │
│ │ awareness & routing    │        │       │          │            │  │
└───────────────────────────────────────────────────────────────────────┘
```

**Per-project init flow:**
```
/toolkit-init
  ├─ Atlas      → .claude/atlas.yaml + registry entry
  ├─ Relay      → .claude/relay.yaml (trackers from git remote)
  ├─ Beads      → .beads/ (bd init)
  ├─ Agent Mail → .git/hooks/pre-commit (guard)
  ├─ Serena     → .serena/project.yml + onboarding
  └─ BMAD       → _bmad/ (workflow templates)
```

## Requirements

- **Claude Code** CLI (`claude`) installed and authenticated
- **Python 3.10+** (toolkit scripts are stdlib-only, no pip install needed)
- **git** (for Beads, Agent Mail, Claudeman installs)
- **npm** (for beads-ui, Claudeman)
- **tmux** (for Claudeman)
- **uv/uvx** (for Serena, Agent Mail — auto-installed on macOS/Linux if missing)

## File Locations

| What | Where |
|------|-------|
| Toolkit plugin | Wherever you cloned it |
| Atlas registry | `~/.claude/atlas/registry.yaml` |
| Atlas providers | `~/.claude/atlas/providers/*.yaml` |
| Atlas cache | `~/.claude/atlas/cache/projects/` |
| Agent Mail server | `~/.mcp_agent_mail/` |
| Agent Mail data | `~/.mcp_agent_mail_git_mailbox_repo/` |
| Claudeman | `~/.claudeman/` |
| Serena global config | `~/.serena/serena_config.yml` |
| Auto-setup marker | `~/.claude/.toolkit-setup-done` |

**Per-project files created by `/toolkit-init`:**

| File | Tool | Purpose |
|------|------|---------|
| `.claude/atlas.yaml` | Atlas | Project metadata (name, summary, tags) |
| `.claude/relay.yaml` | Relay | Issue tracker configuration |
| `.beads/` | Beads | Issue database, config, git hooks |
| `.git/hooks/pre-commit` | Agent Mail | File reservation guard |
| `.serena/project.yml` | Serena | Language config for LSP |
| `_bmad/` | BMAD | SDLC workflow templates |
