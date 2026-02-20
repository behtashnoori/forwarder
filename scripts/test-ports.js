#!/usr/bin/env node

/**
 * تست هماهنگی پورت‌های فرانت و بک‌اند
 * Frontend (Vite) = 8080, Backend (Flask) = 5001
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');
const envPath = path.join(projectRoot, '.env');

const FRONTEND_PORT = 8080;   // vite.config.ts server.port
const BACKEND_PORT_DEFAULT = 5001;

function loadEnv() {
  const out = {};
  if (!fs.existsSync(envPath)) return out;
  const text = fs.readFileSync(envPath, 'utf8').replace(/\r\n/g, '\n');
  for (const line of text.split('\n')) {
    const m = line.replace(/\r$/, '').match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (m) out[m[1].trim()] = m[2].trim().replace(/^["']|["']$/g, '');
  }
  return out;
}

function parsePortFromUrl(url) {
  const match = url.match(/:(\d+)/);
  return match ? parseInt(match[1], 10) : null;
}

async function checkBackendHealth(baseUrl, origin) {
  try {
    const res = await fetch(`${baseUrl}/api/health`, {
      method: 'GET',
      headers: { Origin: origin },
    });
    return { ok: res.ok, status: res.status, body: await res.text() };
  } catch (e) {
    return { ok: false, status: 0, error: e.message };
  }
}

async function main() {
  const env = { ...process.env, ...loadEnv() };
  const backendPort = parseInt(env.FLASK_RUN_PORT || String(BACKEND_PORT_DEFAULT), 10) || BACKEND_PORT_DEFAULT;
  const viteApiUrl = env.VITE_API_URL || `http://127.0.0.1:${BACKEND_PORT_DEFAULT}`;
  const corsOrigin = (env.CORS_ORIGIN || '').trim();

  const backendBase = `http://127.0.0.1:${backendPort}`;
  const frontendOrigin = `http://localhost:${FRONTEND_PORT}`;

  console.log('🔌 تست هماهنگی فرانت و بک‌اند (پورت‌ها)\n');
  console.log('  فرانت (Vite):     پورت', FRONTEND_PORT, '→', `http://localhost:${FRONTEND_PORT}/`);
  console.log('  بک‌اند (Flask):   پورت', backendPort, '→', backendBase + '/');
  console.log('');

  let failed = false;

  // 1) VITE_API_URL باید به همان پورت بک‌اند اشاره کند
  const apiUrlPort = parsePortFromUrl(viteApiUrl);
  if (apiUrlPort !== backendPort) {
    console.log('❌ VITE_API_URL با پورت بک‌اند همخوان نیست.');
    console.log('   VITE_API_URL:', viteApiUrl, '→ پورت', apiUrlPort);
    console.log('   انتظار پورت بک‌اند:', backendPort);
    failed = true;
  } else {
    console.log('✅ VITE_API_URL با پورت بک‌اند هماهنگ است:', viteApiUrl);
  }

  // 2) CORS باید origin فرانت (localhost:8080 و 127.0.0.1:8080) را داشته باشد
  const corsOrigins = corsOrigin.split(',').map(s => s.trim());
  const hasLocalhost8080 = corsOrigins.some(o => o.includes('localhost:8080') || o.includes('127.0.0.1:8080'));
  if (!hasLocalhost8080) {
    console.log('❌ CORS_ORIGIN باید شامل فرانت باشد: http://localhost:8080 و/یا http://127.0.0.1:8080');
    console.log('   فعلی:', corsOrigin || '(خالی)');
    failed = true;
  } else {
    console.log('✅ CORS_ORIGIN شامل پورت فرانت (8080) است.');
  }

  // 3) درخواست واقعی به بک‌اند با Origin فرانت
  console.log('\n  درخواست به بک‌اند با Origin فرانت...');
  const health = await checkBackendHealth(backendBase, frontendOrigin);
  if (!health.ok) {
    console.log('❌ بک‌اند در دسترس نیست یا خطا برگرداند.');
    console.log('   آدرس:', backendBase + '/api/health');
    if (health.status) console.log('   وضعیت HTTP:', health.status);
    if (health.error) console.log('   خطا:', health.error);
    failed = true;
  } else {
    console.log('✅ بک‌اند پاسخ داد (فرانت می‌تواند به API وصل شود).');
    if (health.body) console.log('   پاسخ:', health.body.slice(0, 80));
  }

  console.log('\n' + (failed ? '⚠️  برخی بررسی‌ها ناموفق بودند.' : '🎉 هماهنگی فرانت و بک‌اند درست است.'));
  setTimeout(() => process.exit(failed ? 1 : 0), 50);
}

main().catch((e) => {
  console.error('خطا:', e);
  process.exit(1);
});
