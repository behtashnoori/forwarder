#!/usr/bin/env node

/** Explicitly create local .env from the tracked safe template. */
import { constants, copyFileSync, chmodSync, existsSync } from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const scriptPath = fileURLToPath(import.meta.url);
const projectRoot = path.resolve(path.dirname(scriptPath), '..');

export function createEnvFile({ root = projectRoot, force = false } = {}) {
  const envPath = path.join(root, '.env');
  const templatePath = path.join(root, '.env.example');

  if (!existsSync(templatePath)) {
    throw new Error('Safe environment template .env.example was not found.');
  }
  if (existsSync(envPath) && !force) {
    throw new Error('Refusing to overwrite existing .env; pass --force explicitly.');
  }

  copyFileSync(templatePath, envPath, force ? 0 : constants.COPYFILE_EXCL);
  if (process.platform !== 'win32') chmodSync(envPath, 0o600);
  return envPath;
}

export function main(argv = process.argv.slice(2)) {
  if (argv.some((arg) => arg !== '--force')) {
    console.error('Usage: npm run setup:env -- [--force]');
    return 2;
  }
  try {
    createEnvFile({ force: argv.includes('--force') });
    console.log('Local .env created from .env.example. Replace placeholders locally.');
    return 0;
  } catch (error) {
    console.error(`Environment setup failed: ${error.message}`);
    return 1;
  }
}

const invokedPath = process.argv[1] ? pathToFileURL(path.resolve(process.argv[1])).href : '';
if (import.meta.url === invokedPath) process.exitCode = main();
