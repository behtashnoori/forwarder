import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const canonicalMigrations = path.join(root, 'backend', 'migrations');
const deprecatedMigrations = path.join(root, 'migrations');

function fail(message) {
  console.error(`❌ ${message}`);
  process.exitCode = 1;
}

function ok(message) {
  console.log(`✅ ${message}`);
}

if (!fs.existsSync(canonicalMigrations)) {
  fail('Canonical migrations directory not found: backend/migrations');
} else {
  ok('Canonical migrations directory exists: backend/migrations');
}

if (fs.existsSync(deprecatedMigrations)) {
  const deprecatedVersions = path.join(deprecatedMigrations, 'versions');
  if (fs.existsSync(deprecatedVersions)) {
    const files = fs.readdirSync(deprecatedVersions).filter((f) => f.endsWith('.py') && f !== '__init__.py');
    if (files.length > 0) {
      console.warn('⚠️ Deprecated root migrations contain version files. Do not add new migrations here.');
      console.warn(`   Found ${files.length} file(s) under migrations/versions`);
    }
  }
  ok('Deprecated root migrations directory detected and flagged.');
}

const alembicInRoot = fs.existsSync(path.join(root, 'migrations', 'alembic.ini'));
const alembicInBackend = fs.existsSync(path.join(root, 'backend', 'migrations', 'alembic.ini'));

if (!alembicInBackend) {
  fail('Missing backend/migrations/alembic.ini');
} else {
  ok('backend/migrations/alembic.ini exists');
}

if (alembicInRoot) {
  console.warn('⚠️ Root migrations/alembic.ini exists. Keep backend/migrations as single source of truth.');
}

if (!process.exitCode) {
  ok('Structure check passed');
}
