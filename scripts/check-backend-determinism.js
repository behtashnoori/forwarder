#!/usr/bin/env node
/**
 * Regression check: ensure no forbidden patterns that break deterministic port/startup.
 * Run in CI or pre-commit. Exits 1 if any pattern is found.
 * Forbidden: use_reloader=True, random/dynamic port selection, multiple port sources in code.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');

const forbidden = [
  {
    pattern: /use_reloader\s*=\s*True/g,
    message: 'Do not set use_reloader=True in code. Use --reload CLI flag only (backend/run.py).',
    files: ['backend/wsgi.py', 'backend/run.py'],
  },
  {
    pattern: /app\.run\s*\([^)]*port\s*=\s*0\s*\)/g,
    message: 'Do not bind to port 0 (random port). Use config.PORT (default 8000).',
    files: ['backend/**/*.py'],
  },
  {
    pattern: /random\.randint\s*\(\s*\d+\s*,\s*\d+\s*\).*port|port.*random/g,
    message: 'Do not select port randomly.',
    files: ['backend/**/*.py'],
  },
];

function* walk(dir, ext = '.py') {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory() && !e.name.startsWith('.') && e.name !== 'node_modules' && e.name !== '__pycache__') {
      yield* walk(full, ext);
    } else if (e.isFile() && e.name.endsWith(ext)) {
      yield path.relative(rootDir, full);
    }
  }
}

let failed = false;
const relPaths = [...walk(backendDir)].filter((r) => !r.includes('migrations'));
for (const rel of relPaths) {
  const content = fs.readFileSync(path.join(rootDir, rel), 'utf8');
  for (const { pattern, message } of forbidden) {
    if (pattern.test(content)) {
      console.error(`[FORBIDDEN] ${rel}: ${message}`);
      failed = true;
    }
  }
  if (rel === 'backend/wsgi.py' && content.includes('os.getenv("PORT")') && !content.includes('backend.run')) {
    console.error('[FORBIDDEN] backend/wsgi.py: Do not read PORT here. Use backend.run (canonical entrypoint).');
    failed = true;
  }
}

if (failed) {
  console.error('Run: npm run backend or python -m backend.run. Change port only in .env (PORT=8000).');
  process.exit(1);
}
console.log('check-backend-determinism: OK (no forbidden patterns)');
