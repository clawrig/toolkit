#!/usr/bin/env python3
"""Batch project initialization — scan subdirectories for git repos and init each one."""

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
DEPTH = 2  # How many levels deep to scan for git repos

for a in args:
    if a.startswith("--depth="):
        try:
            DEPTH = int(a.split("=", 1)[1])
        except ValueError:
            pass

HOME = os.path.expanduser("~")
SCAN_ROOT = os.getcwd()

# ── Helpers ───────────────────────────────────────────────────────────────────


def _slug_from_dirname(path: str) -> str:
    name = os.path.basename(os.path.abspath(path))
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def _detect_project_name(project_dir: str) -> str:
    """Try package.json name, fallback to dirname."""
    pkg = os.path.join(project_dir, "package.json")
    if os.path.isfile(pkg):
        try:
            data = json.loads(open(pkg).read())
            if data.get("name"):
                return data["name"]
        except (json.JSONDecodeError, OSError):
            pass
    return os.path.basename(os.path.abspath(project_dir))


def _detect_tags(project_dir: str) -> list[str]:
    """Auto-detect project tags from files present."""
    tags = []
    checks = [
        (["package.json", "tsconfig.json"], "typescript"),
        (["Cargo.toml"], "rust"),
        (["go.mod"], "go"),
        (["build.gradle", "build.gradle.kts"], "java"),
        (["requirements.txt", "pyproject.toml"], "python"),
        (["build.sbt"], "scala"),
        (["Gemfile"], "ruby"),
        (["composer.json"], "php"),
        (["Package.swift"], "swift"),
        (["mix.exs"], "elixir"),
        (["pubspec.yaml"], "dart"),
    ]
    for files, tag in checks:
        if any(os.path.isfile(os.path.join(project_dir, f)) for f in files):
            tags.append(tag)
    if not tags:
        if any(os.path.isfile(os.path.join(project_dir, f)) for f in ["CMakeLists.txt", "Makefile"]):
            tags.append("cpp")
    return tags


# Tag → Serena language name mapping
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


def _registry_has_slug(registry_path: str, slug: str) -> bool:
    if not os.path.isfile(registry_path):
        return False
    content = open(registry_path).read()
    return bool(re.search(rf"^  {re.escape(slug)}:", content, re.M))


def _registry_has_path(registry_path: str, path: str) -> bool:
    if not os.path.isfile(registry_path):
        return False
    content = open(registry_path).read()
    tilde_path = path.replace(HOME, "~")
    return tilde_path in content or path in content


# ── Scan for git repos ───────────────────────────────────────────────────────


def find_git_repos(root: str, max_depth: int) -> list[str]:
    """Find directories containing .git/ up to max_depth levels deep."""
    repos = []

    def _scan(path: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return

        if ".git" in entries and os.path.isdir(os.path.join(path, ".git")):
            repos.append(path)
            return  # Don't scan inside a git repo for nested repos

        for entry in entries:
            if entry.startswith(".") or entry == "node_modules" or entry == "vendor":
                continue
            full = os.path.join(path, entry)
            if os.path.isdir(full) and not os.path.islink(full):
                _scan(full, depth + 1)

    _scan(root, 0)
    return repos


# ── Per-project init functions ───────────────────────────────────────────────


def init_atlas(project_dir: str):
    if not check_plugin("atlas"):
        return False

    atlas_dir = os.path.join(HOME, ".claude", "atlas")
    registry_path = os.path.join(atlas_dir, "registry.yaml")
    cache_dir = os.path.join(atlas_dir, "cache", "projects")
    project_config = os.path.join(project_dir, ".claude", "atlas.yaml")

    os.makedirs(cache_dir, exist_ok=True)

    if not os.path.isfile(registry_path):
        with open(registry_path, "w") as f:
            f.write("# Atlas project registry\n\nprojects:\n")

    if _registry_has_path(registry_path, project_dir):
        return True  # Already registered

    name = _detect_project_name(project_dir)
    slug = _slug_from_dirname(project_dir)
    remote = git_remote_url(project_dir)
    tags = _detect_tags(project_dir)

    if _registry_has_slug(registry_path, slug):
        slug = slug + "-2"

    # Write .claude/atlas.yaml if missing
    os.makedirs(os.path.join(project_dir, ".claude"), exist_ok=True)
    if not os.path.isfile(project_config):
        tags_str = ", ".join(tags) if tags else ""
        yaml_content = f"name: {name}\nsummary: \"Initialized by toolkit\"\n"
        if tags_str:
            yaml_content += f"tags: [{tags_str}]\n"
        with open(project_config, "w") as f:
            f.write(yaml_content)

    # Add to registry
    tilde_path = project_dir.replace(HOME, "~")
    entry = f"  {slug}:\n    path: {tilde_path}\n"
    if remote:
        entry += f"    repo: {remote}\n"
    with open(registry_path, "a") as f:
        f.write(entry)

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

    return True


def init_relay(project_dir: str):
    if not check_plugin("relay"):
        return False

    relay_config = os.path.join(project_dir, ".claude", "relay.yaml")
    if os.path.isfile(relay_config):
        return True  # Already configured

    remote = git_remote_url(project_dir)
    host = detect_repo_host(remote) if remote else None
    org_repo = extract_org_repo(remote) if remote else None
    has_beads = command_exists("bd")

    trackers = []
    if host and org_repo:
        tracker = {"name": host, "type": host, "default": True}
        if host == "github":
            tracker["repo"] = org_repo
        elif host == "gitlab":
            tracker["project_id"] = org_repo
        trackers.append(tracker)
        if has_beads:
            trackers.append({"name": "beads", "type": "beads", "scope": "local"})
    elif has_beads:
        trackers.append({"name": "beads", "type": "beads", "scope": "local", "default": True})

    if not trackers:
        return False

    os.makedirs(os.path.join(project_dir, ".claude"), exist_ok=True)
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

    return True


def init_beads(project_dir: str):
    if not command_exists("bd"):
        return False
    if os.path.isdir(os.path.join(project_dir, ".beads")):
        return True  # Already initialized

    name = _detect_project_name(project_dir)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return bool(run(f'cd "{project_dir}" && bd init --quiet {slug}'))


def _pre_commit_has_guard(project_dir: str) -> bool:
    pre_commit = os.path.join(project_dir, ".git", "hooks", "pre-commit")
    if not os.path.isfile(pre_commit):
        return False
    try:
        content = open(pre_commit).read()
        return "agent-mail" in content or "agent_mail" in content
    except OSError:
        return False


def init_agent_mail(project_dir: str):
    if not check_mail_installed() or not mail_server_alive():
        return False

    if _pre_commit_has_guard(project_dir):
        return True  # Already installed

    run(
        f'cd {MAIL_DIR} && uv run python -m mcp_agent_mail.cli guard install '
        f'"{project_dir}" "{project_dir}"'
    )
    # Verify the guard was actually written (command may silently skip)
    return _pre_commit_has_guard(project_dir)


def init_serena(project_dir: str):
    if not check_plugin("serena"):
        return False

    project_yml = os.path.join(project_dir, ".serena", "project.yml")
    if os.path.isfile(project_yml):
        return True  # Already exists

    tags = _detect_tags(project_dir)
    languages = []
    for tag in tags:
        lang = TAG_TO_SERENA.get(tag)
        if lang and lang not in languages:
            languages.append(lang)

    if not languages:
        return False

    name = _detect_project_name(project_dir)
    serena_dir = os.path.join(project_dir, ".serena")
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

    gitignore = os.path.join(serena_dir, ".gitignore")
    if not os.path.isfile(gitignore):
        with open(gitignore, "w") as f:
            f.write("cache/\nmemories/\n")

    return True


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    log()
    log(f"  {BOLD}Project Init — Batch Scanner{RESET}")
    log(f"  {'=' * 28}")
    log(f"  Scanning: {DIM}{SCAN_ROOT}{RESET} (depth={DEPTH})")
    log()

    repos = find_git_repos(SCAN_ROOT, DEPTH)

    if not repos:
        log(f"  {YELLOW}No git repos found{RESET} in {SCAN_ROOT} (depth={DEPTH})")
        log(f"  Try increasing depth: --depth=3")
        log()
        return

    log(f"  Found {BOLD}{len(repos)}{RESET} git repos:")
    for r in repos:
        rel = os.path.relpath(r, SCAN_ROOT)
        log(f"    {DIM}{rel}{RESET}")
    log()

    # Check available tools once
    has_atlas = check_plugin("atlas")
    has_relay = check_plugin("relay")
    has_beads = command_exists("bd")
    has_mail = check_mail_installed() and mail_server_alive()
    has_serena = check_plugin("serena")

    tools = []
    if has_atlas and not RELAY_ONLY:
        tools.append("atlas")
    if has_relay and not ATLAS_ONLY:
        tools.append("relay")
    if has_beads:
        tools.append("beads")
    if has_mail:
        tools.append("mail-guard")
    if has_serena:
        tools.append("serena")

    log(f"  Available tools: {CYAN}{', '.join(tools) or 'none'}{RESET}")
    log()

    results = []

    for repo_path in repos:
        rel = os.path.relpath(repo_path, SCAN_ROOT)
        status = {}

        if has_atlas and not RELAY_ONLY:
            status["atlas"] = init_atlas(repo_path)
        if has_relay and not ATLAS_ONLY:
            status["relay"] = init_relay(repo_path)
        if has_beads:
            status["beads"] = init_beads(repo_path)
        if has_mail:
            status["mail"] = init_agent_mail(repo_path)
        if has_serena:
            status["serena"] = init_serena(repo_path)

        results.append((rel, status))

    # Summary table
    log(f"  {BOLD}Results{RESET}")
    log(f"  {'─' * 60}")

    for rel, status in results:
        checks = []
        for tool, ok in status.items():
            if ok:
                checks.append(f"{GREEN}✓{RESET}{tool}")
            else:
                checks.append(f"{DIM}·{tool}{RESET}")
        checks_str = "  ".join(checks)
        log(f"  {rel:<40} {checks_str}")

    initialized = sum(1 for _, s in results if any(s.values()))
    skipped = len(results) - initialized
    log()
    log(f"  {GREEN}{initialized} initialized{RESET}, {DIM}{skipped} already up to date{RESET}")
    log()


if __name__ == "__main__":
    main()
