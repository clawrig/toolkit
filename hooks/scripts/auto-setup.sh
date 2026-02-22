#!/usr/bin/env bash
# Auto-setup: checks and installs missing Claude Code tools on session start.
# Non-interactive — installs standard tools only.
# Uses a marker file to avoid re-checking every session.

set -euo pipefail

MARKER="$HOME/.claude/.toolkit-setup-done"
MAX_AGE_DAYS=7

# Skip if marker exists and is recent
if [[ -f "$MARKER" ]]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    age=$(( ($(date +%s) - $(stat -f %m "$MARKER")) / 86400 ))
  else
    age=$(( ($(date +%s) - $(stat -c %Y "$MARKER")) / 86400 ))
  fi
  if (( age < MAX_AGE_DAYS )); then
    exit 0
  fi
fi

command_exists() { command -v "$1" &>/dev/null; }

configure_serena() {
  local config="$HOME/.serena/serena_config.yml"
  [[ -f "$config" ]] || return 0
  if grep -q '^web_dashboard_open_on_launch: true' "$config" 2>/dev/null; then
    sed -i.bak 's/^web_dashboard_open_on_launch: true$/web_dashboard_open_on_launch: false/' "$config"
    rm -f "${config}.bak"
    echo "  Configured Serena: web_dashboard_open_on_launch = false"
  fi
}

check_mcp() {
  claude mcp list 2>/dev/null | grep -qi "$1"
}

check_plugin() {
  claude plugin list 2>/dev/null | grep -qi "$1"
}

check_marketplace() {
  claude plugin marketplace list 2>/dev/null | grep -qi "$1"
}

missing=()
installed=()

# --- Context7 ---
if check_mcp "context7"; then
  installed+=("Context7")
else
  echo "Installing Context7..."
  if claude mcp add --scope user --transport http context7 https://mcp.context7.com/mcp 2>/dev/null; then
    installed+=("Context7")
  else
    missing+=("Context7")
  fi
fi

# --- Serena ---
if check_mcp "serena"; then
  configure_serena
  installed+=("Serena")
else
  if command_exists uvx; then
    echo "Installing Serena..."
    if claude mcp add --scope user serena -- uvx --from "git+https://github.com/oraios/serena" serena start-mcp-server --context claude-code --project-from-cwd 2>/dev/null; then
      configure_serena
      installed+=("Serena")
    else
      missing+=("Serena")
    fi
  else
    echo "Serena: skipped (uvx not found — install uv first)"
    missing+=("Serena")
  fi
fi

# --- Beads ---
if command_exists bd && check_plugin "beads"; then
  installed+=("Beads")
else
  if command_exists bd; then
    echo "Installing Beads plugin..."
    if ! check_marketplace "steveyegge/beads"; then
      claude plugin marketplace add steveyegge/beads 2>/dev/null || true
    fi
    if claude plugin install beads 2>/dev/null; then
      installed+=("Beads")
    else
      missing+=("Beads")
    fi
  else
    echo "Beads: skipped (bd CLI not found)"
    missing+=("Beads")
  fi
fi

# --- beads-ui ---
if command_exists bdui; then
  installed+=("beads-ui")
else
  if command_exists npm; then
    echo "Installing beads-ui..."
    if npm i -g beads-ui 2>/dev/null; then
      installed+=("beads-ui")
    else
      missing+=("beads-ui")
    fi
  else
    missing+=("beads-ui")
  fi
fi

# --- BMAD-METHOD (per-project, skip in auto-setup) ---
# BMAD is per-project and interactive — not auto-installed.
# Use /toolkit-setup to install it manually.

# Summary
echo ""
echo "Toolkit auto-setup:"
if (( ${#installed[@]} > 0 )); then
  echo "  Ready: ${installed[*]}"
fi
if (( ${#missing[@]} > 0 )); then
  echo "  Missing: ${missing[*]} (run /toolkit-setup to install)"
fi

# Write marker
mkdir -p "$(dirname "$MARKER")"
touch "$MARKER"
