#!/usr/bin/env python3
"""Per-project initialization — register in Atlas, configure Relay trackers."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import (
    BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW,
    MAIL_DIR, check_mail_installed, check_mcp, check_plugin,
    command_exists, detect_repo_host, extract_org_repo,
    git_remote_url, log, mail_server_alive, run,
)

# ── CLI args ──────────────────────────────────────────────────────────────────

args = sys.argv[1:]
NON_INTERACTIVE = "--non-interactive" in args
ATLAS_ONLY = "--atlas-only" in args
RELAY_ONLY = "--relay-only" in args
SKIP_BMAD = "--no-bmad" in args

HOME = os.path.expanduser("~")
CWD = os.getcwd()

# ── Helpers ───────────────────────────────────────────────────────────────────


def _slug_from_dirname(path: str) -> str:
    name = os.path.basename(os.path.abspath(path))
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def _detect_project_name() -> str:
    """Try package.json name, fallback to dirname."""
    pkg = os.path.join(CWD, "package.json")
    if os.path.isfile(pkg):
        try:
            data = json.loads(open(pkg).read())
            if data.get("name"):
                return data["name"]
        except (json.JSONDecodeError, OSError):
            pass
    return os.path.basename(os.path.abspath(CWD))


def _detect_tags() -> list[str]:
    """Auto-detect project tags from files present."""
    tags = []
    if os.path.isfile(os.path.join(CWD, "package.json")) or os.path.isfile(os.path.join(CWD, "tsconfig.json")):
        tags.append("typescript")
    elif os.path.isfile(os.path.join(CWD, "package.json")):
        tags.append("javascript")
    if os.path.isfile(os.path.join(CWD, "Cargo.toml")):
        tags.append("rust")
    if os.path.isfile(os.path.join(CWD, "go.mod")):
        tags.append("go")
    if os.path.isfile(os.path.join(CWD, "build.gradle")) or os.path.isfile(os.path.join(CWD, "build.gradle.kts")):
        tags.append("java")
    if os.path.isfile(os.path.join(CWD, "requirements.txt")) or os.path.isfile(os.path.join(CWD, "pyproject.toml")):
        tags.append("python")
    if os.path.isfile(os.path.join(CWD, "build.sbt")):
        tags.append("scala")
    if os.path.isfile(os.path.join(CWD, "Gemfile")):
        tags.append("ruby")
    if os.path.isfile(os.path.join(CWD, "composer.json")):
        tags.append("php")
    if os.path.isfile(os.path.join(CWD, "Package.swift")):
        tags.append("swift")
    if os.path.isfile(os.path.join(CWD, "CMakeLists.txt")) or os.path.isfile(os.path.join(CWD, "Makefile")):
        # Only add cpp if no other language detected (Makefile is ambiguous)
        if not tags:
            tags.append("cpp")
    if os.path.isfile(os.path.join(CWD, "mix.exs")):
        tags.append("elixir")
    if os.path.isfile(os.path.join(CWD, "pubspec.yaml")):
        tags.append("dart")
    return tags


# Tag → Serena language name mapping
# Serena uses "typescript" for JS too, "cpp" for C too
TAG_TO_SERENA = {
    "typescript": "typescript",
    "javascript": "typescript",
    "python": "python",
    "rust": "rust",
    "go": "go",
    "java": "java",
    "scala": "scala",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "cpp": "cpp",
    "elixir": "elixir",
    "dart": "dart",
    "kotlin": "kotlin",
}


def _read_yaml_simple(path: str) -> dict | None:
    """Minimal YAML reader for simple key: value and projects: block.
    Only handles what we need — NOT a full YAML parser."""
    if not os.path.isfile(path):
        return None
    try:
        return {"_raw": open(path).read()}
    except OSError:
        return None


def _registry_has_slug(registry_path: str, slug: str) -> bool:
    """Check if slug already exists in registry.yaml."""
    if not os.path.isfile(registry_path):
        return False
    content = open(registry_path).read()
    # Look for "  slug:" pattern (2-space indent under projects:)
    return bool(re.search(rf"^  {re.escape(slug)}:", content, re.M))


def _registry_has_path(registry_path: str, path: str) -> bool:
    """Check if path already registered."""
    if not os.path.isfile(registry_path):
        return False
    content = open(registry_path).read()
    # Normalize: replace home with ~
    tilde_path = path.replace(HOME, "~")
    return tilde_path in content or path in content


# ── Atlas ─────────────────────────────────────────────────────────────────────


def init_atlas():
    log(f"\n  {BOLD}Atlas{RESET}")
    log("  ─────")

    if not check_plugin("atlas"):
        log(f"  {DIM}Atlas plugin not installed — skipping{RESET}")
        log(f"  {DIM}Install with: claude plugin install atlas{RESET}")
        return

    atlas_dir = os.path.join(HOME, ".claude", "atlas")
    registry_path = os.path.join(atlas_dir, "registry.yaml")
    cache_dir = os.path.join(atlas_dir, "cache", "projects")
    project_config = os.path.join(CWD, ".claude", "atlas.yaml")

    # Ensure directories exist
    os.makedirs(cache_dir, exist_ok=True)

    # Create registry if missing
    if not os.path.isfile(registry_path):
        with open(registry_path, "w") as f:
            f.write("# Atlas project registry\n\nprojects:\n")
        log("  Created registry.yaml")

    # Check if already registered
    if _registry_has_path(registry_path, CWD):
        log(f"  {GREEN}✓{RESET} Project already registered in atlas")
        if os.path.isfile(project_config):
            log(f"  {DIM}Config: .claude/atlas.yaml{RESET}")
        return

    # Detect project info
    name = _detect_project_name()
    slug = _slug_from_dirname(CWD)
    remote = git_remote_url(CWD)
    tags = _detect_tags()

    # Avoid slug collision
    if _registry_has_slug(registry_path, slug):
        slug = slug + "-2"

    log(f"  Registering: {CYAN}{name}{RESET} (slug: {slug})")

    # Get summary
    if NON_INTERACTIVE:
        summary = "Initialized by toolkit"
    else:
        try:
            summary = input(f"  Summary (<100 chars): ").strip()
        except (EOFError, KeyboardInterrupt):
            summary = "Initialized by toolkit"
        if not summary:
            summary = "Initialized by toolkit"

    # Write .claude/atlas.yaml
    os.makedirs(os.path.join(CWD, ".claude"), exist_ok=True)
    if not os.path.isfile(project_config):
        tags_str = ", ".join(tags) if tags else ""
        yaml_content = f"name: {name}\nsummary: \"{summary}\"\n"
        if tags_str:
            yaml_content += f"tags: [{tags_str}]\n"
        with open(project_config, "w") as f:
            f.write(yaml_content)
        log(f"  Created .claude/atlas.yaml")
    else:
        log(f"  {DIM}.claude/atlas.yaml already exists{RESET}")

    # Add to registry
    tilde_path = CWD.replace(HOME, "~")
    entry = f"  {slug}:\n    path: {tilde_path}\n"
    if remote:
        entry += f"    repo: {remote}\n"
    with open(registry_path, "a") as f:
        f.write(entry)
    log(f"  Added to registry")

    # Cache
    if os.path.isfile(project_config):
        import time
        cache_file = os.path.join(cache_dir, f"{slug}.yaml")
        meta = (
            f"_cache_meta:\n"
            f"  source: {project_config}\n"
            f"  cached_at: \"{time.strftime('%Y-%m-%dT%H:%M:%S')}\"\n"
        )
        if remote:
            meta += f"  repo: {remote}\n"
        meta += "\n"
        with open(cache_file, "w") as f:
            f.write(meta)
            f.write(open(project_config).read())
        log(f"  Cached to ~/.claude/atlas/cache/projects/{slug}.yaml")

    log(f"  {GREEN}✓{RESET} Atlas registration complete")


# ── Relay ─────────────────────────────────────────────────────────────────────


def init_relay():
    log(f"\n  {BOLD}Relay{RESET}")
    log("  ─────")

    if not check_plugin("relay"):
        log(f"  {DIM}Relay plugin not installed — skipping{RESET}")
        log(f"  {DIM}Install with: claude plugin install relay{RESET}")
        return

    relay_config = os.path.join(CWD, ".claude", "relay.yaml")

    if os.path.isfile(relay_config):
        log(f"  {GREEN}✓{RESET} .claude/relay.yaml already exists")
        return

    # Detect from git remote
    remote = git_remote_url(CWD)
    host = detect_repo_host(remote) if remote else None
    org_repo = extract_org_repo(remote) if remote else None
    has_beads = command_exists("bd")

    trackers = []

    if host and org_repo:
        log(f"  Detected: {CYAN}{host}{RESET} ({org_repo})")

        if NON_INTERACTIVE:
            # Auto-configure detected tracker as default
            tracker = {"name": host, "type": host, "default": True}
            if host == "github":
                tracker["repo"] = org_repo
            elif host == "gitlab":
                tracker["project_id"] = org_repo
            trackers.append(tracker)

            if has_beads:
                trackers.append({"name": "beads", "type": "beads", "scope": "local"})
        else:
            log(f"  Available trackers:")
            options = []
            if host in ("github", "gitlab"):
                options.append(host)
            if has_beads:
                options.append("beads")
            log(f"    {', '.join(options)}")
            try:
                answer = input(f"  Configure which? (space-separated, \"all\", or \"q\"): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "q"

            if not answer or answer == "q":
                log("  Skipped.")
                return

            selected = options if answer == "all" else answer.split()
            for t in selected:
                if t == host:
                    tracker = {"name": host, "type": host, "default": True}
                    if host == "github":
                        tracker["repo"] = org_repo
                    elif host == "gitlab":
                        tracker["project_id"] = org_repo
                    trackers.append(tracker)
                elif t == "beads":
                    trackers.append({"name": "beads", "type": "beads", "scope": "local"})
    elif has_beads:
        log(f"  No git remote detected, configuring beads only")
        trackers.append({"name": "beads", "type": "beads", "scope": "local", "default": True})
    else:
        log(f"  {DIM}No git remote and no beads CLI — nothing to configure{RESET}")
        return

    if not trackers:
        return

    # Write relay.yaml
    os.makedirs(os.path.join(CWD, ".claude"), exist_ok=True)
    lines = ["issue_trackers:"]
    for t in trackers:
        lines.append(f"  - name: {t['name']}")
        lines.append(f"    type: {t['type']}")
        if t.get("default"):
            lines.append("    default: true")
        if t.get("repo"):
            lines.append(f'    repo: "{t["repo"]}"')
        if t.get("project_id"):
            lines.append(f'    project_id: "{t["project_id"]}"')
        if t.get("scope"):
            lines.append(f"    scope: {t['scope']}")

    with open(relay_config, "w") as f:
        f.write("\n".join(lines) + "\n")

    log(f"  Created .claude/relay.yaml")
    log(f"  {GREEN}✓{RESET} Relay configuration complete")


# ── Beads ─────────────────────────────────────────────────────────────────


def init_beads():
    log(f"\n  {BOLD}Beads{RESET}")
    log("  ─────")

    if not command_exists("bd"):
        log(f"  {DIM}bd CLI not installed — skipping{RESET}")
        return

    beads_dir = os.path.join(CWD, ".beads")

    if os.path.isdir(beads_dir):
        log(f"  {GREEN}✓{RESET} .beads/ already initialized")
        return

    # Check we're in a git repo (beads requires git)
    if not os.path.isdir(os.path.join(CWD, ".git")):
        log(f"  {DIM}Not a git repo — beads requires git, skipping{RESET}")
        return

    name = _detect_project_name()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    log(f"  Initializing beads with prefix: {CYAN}{slug}{RESET}")
    if run(f"bd init --quiet {slug}"):
        log(f"  {GREEN}✓{RESET} Beads initialized")
    else:
        log(f"  {YELLOW}!{RESET} bd init failed — run manually: bd init")


# ── Agent Mail ────────────────────────────────────────────────────────────


def init_agent_mail():
    log(f"\n  {BOLD}Agent Mail{RESET}")
    log("  ──────────")

    if not check_mail_installed():
        log(f"  {DIM}Agent Mail not installed — skipping{RESET}")
        return

    if not mail_server_alive():
        log(f"  {YELLOW}!{RESET} Agent Mail server not running (start with /toolkit-setup)")
        return

    # Check we're in a git repo (guard needs .git/)
    if not os.path.isdir(os.path.join(CWD, ".git")):
        log(f"  {DIM}Not a git repo — skipping guard install{RESET}")
        return

    # Check if guard is already installed
    pre_commit = os.path.join(CWD, ".git", "hooks", "pre-commit")
    if os.path.isfile(pre_commit):
        try:
            content = open(pre_commit).read()
            if "agent-mail" in content or "agent_mail" in content:
                log(f"  {GREEN}✓{RESET} Pre-commit guard already installed")
                return
        except OSError:
            pass

    log("  Installing pre-commit guard...")
    if run(
        f"cd {MAIL_DIR} && uv run python -m mcp_agent_mail.cli guard install "
        f'"{CWD}" "{CWD}"'
    ):
        log(f"  {GREEN}✓{RESET} Pre-commit guard installed")
        log(f"  {DIM}Blocks commits conflicting with other agents' file reservations{RESET}")
    else:
        log(f"  {YELLOW}!{RESET} Guard install failed — install manually:")
        log(f"    cd {MAIL_DIR} && uv run python -m mcp_agent_mail.cli guard install \"{CWD}\" \"{CWD}\"")


# ── Serena ────────────────────────────────────────────────────────────────


def init_serena():
    log(f"\n  {BOLD}Serena{RESET}")
    log("  ──────")

    if not check_plugin("serena"):
        log(f"  {DIM}Serena plugin not installed — skipping{RESET}")
        return

    serena_dir = os.path.join(CWD, ".serena")
    project_yml = os.path.join(serena_dir, "project.yml")

    if os.path.isfile(project_yml):
        log(f"  {GREEN}✓{RESET} .serena/project.yml already exists")
        return

    # Detect languages from project files
    tags = _detect_tags()
    languages = []
    for tag in tags:
        lang = TAG_TO_SERENA.get(tag)
        if lang and lang not in languages:
            languages.append(lang)

    if not languages:
        if NON_INTERACTIVE:
            log(f"  {DIM}No languages detected — skipping Serena setup{RESET}")
            return
        try:
            answer = input("  Languages (space-separated, e.g. python typescript): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if not answer:
            log("  Skipped.")
            return
        languages = answer.split()

    name = _detect_project_name()
    log(f"  Languages: {CYAN}{', '.join(languages)}{RESET}")

    # Write .serena/project.yml
    os.makedirs(serena_dir, exist_ok=True)
    lines = [
        f'project_name: "{name}"',
        "languages:",
    ]
    for lang in languages:
        lines.append(f"- {lang}")
    lines += [
        'encoding: "utf-8"',
        "ignore_all_files_in_gitignore: true",
        "ignored_paths: []",
        "read_only: false",
        "excluded_tools: []",
        "included_optional_tools: []",
        "fixed_tools: []",
        "base_modes:",
        "default_modes:",
        'initial_prompt: ""',
        "symbol_info_budget:",
    ]
    with open(project_yml, "w") as f:
        f.write("\n".join(lines) + "\n")

    # Write .serena/.gitignore (cache and logs should not be committed)
    gitignore = os.path.join(serena_dir, ".gitignore")
    if not os.path.isfile(gitignore):
        with open(gitignore, "w") as f:
            f.write("cache/\nmemories/\n")

    log(f"  Created .serena/project.yml")

    # Trigger onboarding — Serena's onboarding discovers project structure,
    # build/test tasks, and stores results in .serena/memories/.
    # It runs as an MCP tool call, so we just tell the user.
    log(f"  {CYAN}→{RESET} Run Serena onboarding in Claude Code to complete setup:")
    log(f"    Ask Claude: \"run serena onboarding for this project\"")

    log(f"  {GREEN}✓{RESET} Serena project setup complete")


# ── BMAD ──────────────────────────────────────────────────────────────────────


def init_bmad():
    log(f"\n  {BOLD}BMAD{RESET}")
    log("  ────")

    if os.path.isdir(os.path.join(CWD, "_bmad")):
        log(f"  {GREEN}✓{RESET} _bmad/ already exists")
        return

    if NON_INTERACTIVE or not sys.stdin.isatty():
        log("  Installing BMAD non-interactively...")
        cmd = f'npx bmad-method install --directory "{CWD}" --modules bmm --tools claude-code --yes'
        if run(cmd):
            log(f"  {GREEN}✓{RESET} BMAD installed")
        else:
            log(f"  {YELLOW}!{RESET} BMAD install failed — run manually: npx bmad-method install")
        return

    log("  Launching BMAD installer...")
    run("npx bmad-method install")


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    log()
    log(f"  {BOLD}Project Init{RESET}")
    log(f"  {'=' * 12}")
    log(f"  {DIM}{CWD}{RESET}")

    if not RELAY_ONLY:
        init_atlas()

    if not ATLAS_ONLY:
        init_relay()

    init_beads()
    init_agent_mail()
    init_serena()

    if not SKIP_BMAD:
        init_bmad()

    log()
    log(f"  {BOLD}Done!{RESET}")
    log()


if __name__ == "__main__":
    main()
