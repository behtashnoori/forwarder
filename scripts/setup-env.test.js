import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createEnvFile, main } from './setup-env.js';

function fixture() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'forwarder-env-test-'));
  const template = 'DATABASE_URL=postgresql://user:change_me@localhost/example_test\n';
  writeFileSync(path.join(root, '.env.example'), template, 'utf8');
  return { root, template };
}

test('copies the safe template exactly', () => {
  const { root, template } = fixture();
  createEnvFile({ root });
  assert.equal(readFileSync(path.join(root, '.env'), 'utf8'), template);
  if (process.platform !== 'win32') {
    assert.equal(statSync(path.join(root, '.env')).mode & 0o777, 0o600);
  }
});

test('refuses to overwrite by default', () => {
  const { root } = fixture();
  writeFileSync(path.join(root, '.env'), 'KEEP=unchanged\n', 'utf8');
  assert.throws(() => createEnvFile({ root }), /Refusing to overwrite/);
  assert.equal(readFileSync(path.join(root, '.env'), 'utf8'), 'KEEP=unchanged\n');
});

test('force only recopies the tracked template', () => {
  const { root, template } = fixture();
  writeFileSync(path.join(root, '.env'), 'OLD=value\n', 'utf8');
  createEnvFile({ root, force: true });
  assert.equal(readFileSync(path.join(root, '.env'), 'utf8'), template);
});

test('unknown options fail without touching the repository', () => {
  assert.equal(main(['--unknown']), 2);
});
