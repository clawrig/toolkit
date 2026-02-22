#!/usr/bin/env bash
# Quick status check for all toolkit-managed tools

command_exists() { command -v "$1" &>/dev/null; }

check_mcp() {
  claude mcp list 2>/dev/null | grep -qi "$1"
}

check_plugin() {
  claude plugin list 2>/dev/null | grep -qi "$1"
}

icon_ok="\033[32m✓\033[0m"
icon_no="\033[90m·\033[0m"
icon_opt="\033[90m[optional]\033[0m"

echo ""
echo "  Toolkit Status"
echo "  =============="
echo ""

# Context7
if check_mcp "context7"; then
  printf "  $icon_ok %-12s Context7 — Up-to-date library docs via MCP\n" "context7"
else
  printf "  $icon_no %-12s Context7 — Up-to-date library docs via MCP\n" "context7"
fi

# Serena
if check_mcp "serena"; then
  printf "  $icon_ok %-12s Serena — Semantic code navigation via LSP\n" "serena"
else
  printf "  $icon_no %-12s Serena — Semantic code navigation via LSP\n" "serena"
fi

# Beads
if command_exists bd && check_plugin "beads"; then
  printf "  $icon_ok %-12s Beads — Git-backed issue tracker + plugin\n" "beads"
elif command_exists bd; then
  printf "  $icon_no %-12s Beads — CLI found, plugin not installed\n" "beads"
else
  printf "  $icon_no %-12s Beads — Not installed\n" "beads"
fi

# beads-ui
if command_exists bdui; then
  printf "  $icon_ok %-12s beads-ui — Browser UI for Beads\n" "beadsui"
else
  printf "  $icon_no %-12s beads-ui — Browser UI for Beads\n" "beadsui"
fi

# BMAD
if [[ -d "$PWD/_bmad" ]]; then
  printf "  $icon_ok %-12s BMAD-METHOD — SDLC workflow framework $icon_opt\n" "bmad"
else
  printf "  $icon_no %-12s BMAD-METHOD — SDLC workflow framework $icon_opt\n" "bmad"
fi

echo ""

# Marker info
MARKER="$HOME/.claude/.toolkit-setup-done"
if [[ -f "$MARKER" ]]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    last_run=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$MARKER")
  else
    last_run=$(stat -c "%y" "$MARKER" | cut -d. -f1)
  fi
  echo "  Last auto-setup: $last_run"
else
  echo "  Auto-setup has not run yet"
fi
echo ""
