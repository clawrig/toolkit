#!/usr/bin/env node

// Claude Toolkit Setup - Zero dependencies, Node built-ins only
import { execSync, spawnSync } from 'node:child_process';
import { createInterface } from 'node:readline';
import { platform } from 'node:os';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

const isWin = platform() === 'win32';
const args = process.argv.slice(2);
const nonInteractive = args.includes('--non-interactive');
const installTarget = args.find((a, i) => args[i - 1] === '--install') || null;

function log(msg = '') {
  process.stdout.write(msg + '\n');
}

function commandExists(cmd) {
  try {
    execSync(isWin ? `where ${cmd}` : `command -v ${cmd}`, { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

function checkMcp(name) {
  try {
    const out = execSync('claude mcp list', { encoding: 'utf8', stdio: 'pipe' });
    return out.toLowerCase().includes(name.toLowerCase());
  } catch {
    return false;
  }
}

function checkPlugin(name) {
  try {
    const out = execSync('claude plugin list', { encoding: 'utf8', stdio: 'pipe' });
    return out.toLowerCase().includes(name.toLowerCase());
  } catch {
    return false;
  }
}

function checkMarketplace(name) {
  try {
    const out = execSync('claude plugin marketplace list', { encoding: 'utf8', stdio: 'pipe' });
    return out.toLowerCase().includes(name.toLowerCase());
  } catch {
    return false;
  }
}

function run(cmd, opts = {}) {
  try {
    execSync(cmd, { stdio: 'inherit', ...opts });
    return true;
  } catch (e) {
    log(`  Warning: command failed: ${cmd}`);
    if (e.stderr) log(`  ${e.stderr.toString().trim()}`);
    return false;
  }
}

async function ensureDep(cmd, installer) {
  if (commandExists(cmd)) return true;
  const plat = platform();
  const installCmd = installer[plat];
  if (!installCmd) {
    log(`  Cannot auto-install ${installer.name} on ${plat}. Install manually.`);
    return false;
  }
  log(`  Installing ${installer.name}...`);
  return run(installCmd);
}

function ask(rl, question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

// ---------------------------------------------------------------------------
// Post-install configuration
// ---------------------------------------------------------------------------

function configureSerena() {
  const configPath = join(homedir(), '.serena', 'serena_config.yml');
  if (!existsSync(configPath)) return;
  try {
    let content = readFileSync(configPath, 'utf8');
    if (/^web_dashboard_open_on_launch:\s*true\s*$/m.test(content)) {
      content = content.replace(
        /^web_dashboard_open_on_launch:\s*true\s*$/m,
        'web_dashboard_open_on_launch: false'
      );
      writeFileSync(configPath, content);
      log('  Configured Serena: web_dashboard_open_on_launch = false');
    }
  } catch {
    // Config not writable — not critical
  }
}

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

const TOOLS = {
  context7: {
    name: 'Context7',
    description: 'Up-to-date library docs via MCP',
    deps: [],
    check: () => checkMcp('context7'),
    install: () =>
      run('claude mcp add --scope user --transport http context7 https://mcp.context7.com/mcp'),
    uninstall: () => run('claude mcp remove --scope user context7'),
    recommended: true,
  },

  serena: {
    name: 'Serena',
    description: 'Semantic code navigation via LSP (30+ languages)',
    deps: ['uvx'],
    check: () => checkMcp('serena'),
    install: async () => {
      const ok = await ensureDep('uvx', {
        name: 'uv (Python package manager)',
        darwin: 'curl -LsSf https://astral.sh/uv/install.sh | sh',
        linux: 'curl -LsSf https://astral.sh/uv/install.sh | sh',
        win32: 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
      });
      if (!ok && !commandExists('uvx')) {
        log('  Skipping Serena: uvx not available');
        return false;
      }
      const result = run(
        'claude mcp add --scope user serena -- uvx --from "git+https://github.com/oraios/serena" serena start-mcp-server --context claude-code --project-from-cwd'
      );
      if (result) configureSerena();
      return result;
    },
    uninstall: () => run('claude mcp remove --scope user serena'),
    recommended: true,
  },

  beads: {
    name: 'Beads',
    description: 'Git-backed issue tracker + Claude plugin (30+ commands)',
    deps: ['bd'],
    check: () => commandExists('bd') && checkPlugin('beads'),
    install: async () => {
      await ensureDep('bd', {
        name: 'Beads CLI (bd)',
        darwin: 'curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash',
        linux: 'curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash',
        win32: 'go install github.com/steveyegge/beads/cmd/bd@latest',
      });
      if (!commandExists('bd')) {
        log('  Skipping Beads plugin: bd CLI not available');
        return false;
      }
      // Add marketplace and install plugin
      if (!checkMarketplace('steveyegge/beads')) {
        run('claude plugin marketplace add steveyegge/beads');
      }
      return run('claude plugin install beads');
    },
    uninstall: () => {
      run('claude plugin uninstall beads');
      run('claude plugin marketplace remove beads-marketplace');
    },
  },

  beadsui: {
    name: 'beads-ui',
    description: 'Browser UI for Beads issues (kanban, epics, search)',
    deps: ['npm'],
    check: () => commandExists('bdui'),
    install: () => run('npm i -g beads-ui'),
    uninstall: () => run('npm uninstall -g beads-ui'),
  },

  bmad: {
    name: 'BMAD-METHOD',
    description: 'SDLC workflow framework (PM, Architect, Dev, QA personas)',
    deps: ['npx'],
    check: () => existsSync(join(process.cwd(), '_bmad')),
    install: () => {
      if (nonInteractive || !process.stdin.isTTY) {
        log('  BMAD requires an interactive terminal (TTY).');
        log('  Run manually: npx bmad-method install');
        return false;
      }
      log('  Launching interactive BMAD installer...');
      const result = spawnSync('npx bmad-method install', {
        stdio: 'inherit',
        shell: true,
      });
      // Verify it actually installed — the installer exits 0 even if aborted
      if (!existsSync(join(process.cwd(), '_bmad'))) {
        log('  BMAD installer finished but _bmad/ was not created.');
        log('  Run manually: npx bmad-method install');
        return false;
      }
      return result.status === 0;
    },
    uninstall: () => {
      const result = spawnSync('npx bmad-method uninstall', {
        stdio: 'inherit',
        shell: true,
      });
      return result.status === 0;
    },
    perProject: true,
    optional: true,
  },

};

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  log();
  log('  Claude Toolkit Setup');
  log('  ====================');
  log();

  // 1. Check prerequisites
  if (!commandExists('claude')) {
    log('Error: `claude` CLI not found.');
    log('Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code');
    process.exit(1);
  }

  // 2. Check current status
  log('Checking installed tools...');
  log();

  const status = {};

  for (const [id, tool] of Object.entries(TOOLS)) {
    let installed = false;
    try {
      installed = await tool.check();
    } catch {
      installed = false;
    }

    const missingDeps = tool.deps.filter((d) => !commandExists(d));
    status[id] = { installed, missingDeps };

    const icon = installed ? '\x1b[32m✓\x1b[0m' : '\x1b[90m·\x1b[0m';
    const parts = [`  ${icon} ${id.padEnd(10)} ${tool.name} - ${tool.description}`];
    if (missingDeps.length) parts.push(`\x1b[33m(needs: ${missingDeps.join(', ')})\x1b[0m`);
    if (tool.recommended) parts.push('\x1b[36m[recommended]\x1b[0m');
    if (tool.optional) parts.push('\x1b[90m[optional]\x1b[0m');
    else if (tool.perProject) parts.push('\x1b[90m[per-project]\x1b[0m');
    log(parts.join(' '));
  }

  log();

  // 3. Determine what to install
  const notInstalled = Object.entries(TOOLS)
    .filter(([id]) => !status[id].installed && !TOOLS[id].optional)
    .map(([id]) => id);

  const notInstalledOptional = Object.entries(TOOLS)
    .filter(([id]) => !status[id].installed && TOOLS[id].optional)
    .map(([id]) => id);

  if (notInstalled.length === 0 && notInstalledOptional.length === 0) {
    log('All tools are already installed!');
    return;
  }

  let selected;

  if (installTarget) {
    // --install <tool-name>: install a specific tool
    selected = [installTarget];
  } else if (nonInteractive) {
    // --non-interactive: install all standard tools without prompting (excludes optional)
    selected = notInstalled;
  } else {
    // Interactive mode
    const rl = createInterface({ input: process.stdin, output: process.stdout });

    const available = [...notInstalled, ...notInstalledOptional];
    log(`Available: ${available.join(', ')}`);
    if (notInstalledOptional.length) {
      log(`\x1b[90m  Optional (not included in "all" — install by name): ${notInstalledOptional.join(', ')}\x1b[0m`);
    }
    const answer = await ask(rl, 'Install (space-separated IDs, "all", or "q" to quit): ');
    rl.close();

    const trimmed = answer.trim().toLowerCase();
    if (!trimmed || trimmed === 'q') {
      log('Cancelled.');
      process.exit(0);
    }

    selected = trimmed === 'all' ? notInstalled : trimmed.split(/\s+/);
  }

  // 4. Install selected tools
  const results = { ok: [], skip: [], fail: [] };

  for (const id of selected) {
    const tool = TOOLS[id];
    if (!tool) {
      log(`\nUnknown tool: ${id}`);
      results.fail.push(id);
      continue;
    }
    if (status[id].installed) {
      log(`\n✓ ${tool.name} already installed, skipping`);
      results.skip.push(id);
      continue;
    }

    log(`\nInstalling ${tool.name}...`);
    const ok = await tool.install();
    if (ok === false) {
      results.fail.push(id);
      log(`✗ ${tool.name} failed`);
    } else {
      results.ok.push(id);
      log(`✓ ${tool.name} done`);
    }
  }

  // 5. Summary
  log();
  log('  Setup complete!');
  log('  ───────────────');
  if (results.ok.length) log(`  Installed: ${results.ok.join(', ')}`);
  if (results.skip.length) log(`  Skipped:   ${results.skip.join(', ')}`);
  if (results.fail.length) log(`  Failed:    ${results.fail.join(', ')}`);
  log();
  log('  Restart Claude Code for MCP servers to connect.');
  log('  Verify with: claude mcp list');
  log();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
