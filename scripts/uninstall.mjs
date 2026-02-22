#!/usr/bin/env node

// Claude Toolkit Uninstall - Zero dependencies, Node built-ins only
import { execSync, spawnSync } from 'node:child_process';
import { createInterface } from 'node:readline';
import { platform } from 'node:os';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const isWin = platform() === 'win32';

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

function run(cmd, opts = {}) {
  try {
    execSync(cmd, { stdio: 'inherit', ...opts });
    return true;
  } catch {
    log(`  Warning: command failed: ${cmd}`);
    return false;
  }
}

function ask(rl, question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

// ---------------------------------------------------------------------------
// Tool definitions (uninstall only)
// ---------------------------------------------------------------------------

const TOOLS = {
  context7: {
    name: 'Context7',
    check: () => checkMcp('context7'),
    uninstall: () => run('claude mcp remove --scope user context7'),
  },

  serena: {
    name: 'Serena',
    check: () => checkMcp('serena'),
    uninstall: () => run('claude mcp remove --scope user serena'),
  },

  beads: {
    name: 'Beads (plugin)',
    check: () => checkPlugin('beads'),
    uninstall: () => {
      run('claude plugin uninstall beads');
      run('claude plugin marketplace remove beads-marketplace');
    },
    note: 'The bd CLI is not removed. Uninstall it separately (brew uninstall beads / npm uninstall -g @beads/bd).',
  },

  beadsui: {
    name: 'beads-ui',
    check: () => commandExists('bdui'),
    uninstall: () => run('npm uninstall -g beads-ui'),
  },

  bmad: {
    name: 'BMAD-METHOD',
    check: () => existsSync(join(process.cwd(), '_bmad')),
    uninstall: () => {
      log('  Launching BMAD uninstaller...');
      const result = spawnSync('npx bmad-method uninstall', {
        stdio: 'inherit',
        shell: true,
      });
      return result.status === 0;
    },
    note: 'BMAD is per-project. Run this from the project directory.',
  },

};

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  log();
  log('  Claude Toolkit Uninstall');
  log('  ========================');
  log();

  if (!commandExists('claude')) {
    log('Error: `claude` CLI not found.');
    process.exit(1);
  }

  // Check what's installed
  log('Checking installed tools...');
  log();

  const installed = [];
  for (const [id, tool] of Object.entries(TOOLS)) {
    let found = false;
    try {
      found = await tool.check();
    } catch {
      found = false;
    }

    const icon = found ? '\x1b[32m✓\x1b[0m' : '\x1b[90m·\x1b[0m';
    log(`  ${icon} ${id.padEnd(10)} ${tool.name}`);
    if (found) installed.push(id);
  }

  log();

  if (installed.length === 0) {
    log('Nothing to uninstall.');
    return;
  }

  const rl = createInterface({ input: process.stdin, output: process.stdout });

  log(`Installed: ${installed.join(', ')}`);
  const answer = await ask(rl, 'Remove (space-separated IDs, "all", or "q" to quit): ');
  rl.close();

  const trimmed = answer.trim().toLowerCase();
  if (!trimmed || trimmed === 'q') {
    log('Cancelled.');
    process.exit(0);
  }

  const selected = trimmed === 'all' ? installed : trimmed.split(/\s+/);

  for (const id of selected) {
    const tool = TOOLS[id];
    if (!tool) {
      log(`\nUnknown tool: ${id}`);
      continue;
    }

    log(`\nRemoving ${tool.name}...`);
    await tool.uninstall();
    log(`✓ ${tool.name} removed`);
    if (tool.note) log(`  Note: ${tool.note}`);
  }

  log();
  log('  Uninstall complete!');
  log('  Restart Claude Code for changes to take effect.');
  log();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
