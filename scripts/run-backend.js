#!/usr/bin/env node
/**
 * Run backend with env loaded from project root .env.
 * Usage: node scripts/run-backend.js
 * Backend runs on PORT from .env (default 8000).
 */
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');
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
const child = spawn(process.platform === 'win32' ? 'python' : 'python3', ['wsgi.py'], {
  cwd: backendDir,
  stdio: 'inherit',
  env: { ...process.env },
});
child.on('exit', (code) => process.exit(code ?? 0));
