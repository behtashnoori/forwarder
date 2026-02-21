#!/usr/bin/env node
/**
 * Canonical dev launcher: runs backend via python -m backend.run (fixed port, no silent exit).
 * Usage: node scripts/run-backend.js [--reload]
 * Backend runs on PORT from .env (default 8000). Change port only in .env.
 */
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const envPath = path.join(rootDir, '.env');

function loadEnv() {
  if (!fs.existsSync(envPath)) return;
  const content = fs.readFileSync(envPath, 'utf8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'")))
      value = value.slice(1, -1);
    if (key) process.env[key] = value;
  }
}

loadEnv();
const port = parseInt(process.env.PORT || process.env.FLASK_RUN_PORT || '8000', 10);

const net = await import('net');
const portInUse = await new Promise((resolve) => {
  const s = net.createServer();
  s.once('error', () => { s.close(); resolve(true); });
  s.once('listening', () => { s.close(); resolve(false); });
  s.listen(port, '0.0.0.0');
});
if (portInUse) {
  console.error(`Port ${port} is already in use. Please stop the process using it.`);
  console.error(`  Windows: Get-NetTCPConnection -LocalPort ${port} | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }`);
  console.error(`  Or: netstat -ano | findstr :${port}`);
  process.exit(1);
}

const child = spawn(process.platform === 'win32' ? 'python' : 'python3', ['-m', 'backend.run', ...process.argv.slice(2)], {
  cwd: rootDir,
  stdio: 'inherit',
  env: { ...process.env },
});
child.on('exit', (code, signal) => {
  if (code !== null && code !== 0) {
    console.error(`Backend exited with code ${code}. Check startup logs above for the root cause.`);
  }
  if (signal) {
    console.error(`Backend killed by signal: ${signal}`);
  }
  process.exit(code ?? 0);
});
