#!/usr/bin/env node

/**
 * 1) List current expert_user data from DB
 * 2) Login as admin via API
 * 3) Create a new expert via API
 * Fix issues if any.
 */

import pg from 'pg';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, '..');
const API_URL = 'http://127.0.0.1:5000';

function getDatabaseUrl() {
  try {
    const envPath = join(projectRoot, '.env');
    const env = readFileSync(envPath, 'utf8');
    const m = env.match(/DATABASE_URL=(.+)/);
    if (m) return m[1].trim();
  } catch (_) {}
  return 'postgresql://postgres:bagheri13@127.0.0.1:5432/forwarder_db';
}

function parsePgUrl(url) {
  return url.replace(/^postgresql\+psycopg2:/, 'postgres:');
}

async function listCurrentUsers() {
  const connectionString = parsePgUrl(getDatabaseUrl());
  const client = new pg.Client({ connectionString });
  await client.connect();
  try {
    const res = await client.query(
      `SELECT id, username, full_name, email, role, is_active, created_at FROM expert_user ORDER BY id`
    );
    return res.rows;
  } finally {
    await client.end();
  }
}

async function adminLogin() {
  const res = await fetch(`${API_URL}/api/expert/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'Pirooz13@!' }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Login failed ${res.status}: ${text}`);
  }
  const data = await res.json();
  if (!data.success || !data.tokens?.access_token) throw new Error('Invalid login response');
  return data.tokens.access_token;
}

async function createExpert(token, payload) {
  const res = await fetch(`${API_URL}/api/user-management/users`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

async function main() {
  console.log('============================================================');
  console.log('۱) بررسی داده‌های فعلی (expert_user)');
  console.log('============================================================\n');

  let users = [];
  try {
    users = await listCurrentUsers();
    console.log(`تعداد کاربران در دیتابیس: ${users.length}`);
    if (users.length === 0) {
      console.log('   (هیچ کاربری وجود ندارد)\n');
    } else {
      users.forEach((u) => {
        console.log(`   - id=${u.id} | ${u.username} | ${u.full_name} | role=${u.role} | active=${u.is_active}`);
      });
      console.log('');
    }
  } catch (e) {
    console.log('خطا در اتصال به دیتابیس:', e.message);
    console.log('(ادامه با تست API)\n');
  }

  console.log('============================================================');
  console.log('۲) ورود به عنوان ادمین (API)');
  console.log('============================================================\n');

  let token;
  try {
    token = await adminLogin();
    console.log('   ورود ادمین موفق. توکن دریافت شد.\n');
  } catch (e) {
    console.log('   خطا در ورود ادمین:', e.message);
    console.log('   مطمئن شوید backend روی', API_URL, 'در حال اجرا است و کاربر admin وجود دارد.\n');
    process.exit(1);
  }

  console.log('============================================================');
  console.log('۳) ایجاد کارشناس جدید (API)');
  console.log('============================================================\n');

  const expertPayload = {
    username: 'expert_test_1',
    password: 'expert123',
    full_name: 'کارشناس تست',
    email: 'expert.test@company.com',
    phone: '09121111111',
    role: 'expert',
    department: 'operations',
    is_active: true,
    specializations: [],
  };

  const { ok, status, data } = await createExpert(token, expertPayload);

  if (ok) {
    console.log('   ایجاد کارشناس موفق.');
    console.log('   پاسخ:', JSON.stringify(data, null, 2));
  } else {
    console.log('   ایجاد کارشناس ناموفق.');
    console.log('   Status:', status);
    console.log('   Response:', JSON.stringify(data, null, 2));
    process.exit(1);
  }

  console.log('\n============================================================');
  console.log('۴) بررسی مجدد لیست کاربران (دیتابیس)');
  console.log('============================================================\n');

  try {
    const usersAfter = await listCurrentUsers();
    console.log(`تعداد کاربران بعد از ایجاد: ${usersAfter.length}`);
    usersAfter.forEach((u) => {
      console.log(`   - id=${u.id} | ${u.username} | ${u.full_name} | role=${u.role}`);
    });
  } catch (e) {
    console.log('خطا در خواندن مجدد دیتابیس:', e.message);
  }

  console.log('\n✅ تست کامل شد.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
