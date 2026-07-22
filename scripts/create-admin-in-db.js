#!/usr/bin/env node

/**
 * Create admin user directly in PostgreSQL.
 * Uses bcryptjs for password hash (compatible with Python bcrypt).
 * Reads DATABASE_URL from .env or uses default.
 */

import pg from 'pg';
import bcrypt from 'bcryptjs';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, '..');

function getDatabaseUrl() {
  try {
    const envPath = join(projectRoot, '.env');
    const env = readFileSync(envPath, 'utf8');
    const m = env.match(/DATABASE_URL=(.+)/);
    if (m) return m[1].trim();
  } catch (_) {}
  throw new Error('DATABASE_URL must be provided through the process environment or local .env.');
}

function parsePgUrl(url) {
  // Normalize SQLAlchemy PostgreSQL driver URLs for the Node pg client.
  const u = url.replace(/^postgresql\+psycopg2:/, 'postgres:');
  return u;
}

const ADMIN = {
  username: 'admin',
  password: process.env.ADMIN_BOOTSTRAP_PASSWORD,
  full_name: 'مدیر سیستم',
  email: 'admin@company.com',
  phone: '09120000000',
  role: 'admin',
  is_active: true,
};

async function main() {
  if (!ADMIN.password) throw new Error('ADMIN_BOOTSTRAP_PASSWORD is required.');
  const rawUrl = getDatabaseUrl();
  const connectionString = parsePgUrl(rawUrl);

  console.log('============================================================');
  console.log('🔧 ایجاد کاربر Admin در دیتابیس');
  console.log('============================================================');
  console.log('Database:', connectionString.replace(/:[^:@]+@/, ':****@'));
  console.log('');

  const client = new pg.Client({ connectionString });

  try {
    await client.connect();
    console.log('✅ اتصال به دیتابیس برقرار شد.\n');

    // Hash password (compatible with Python bcrypt)
    const password_hash = await bcrypt.hash(ADMIN.password, 10);
    const now = new Date().toISOString().slice(0, 19).replace('T', ' ');

    // Check if admin exists
    const existing = await client.query(
      `SELECT id, username, full_name, role, is_active FROM expert_user WHERE username = $1`,
      [ADMIN.username]
    );

    if (existing.rows.length > 0) {
      const row = existing.rows[0];
      console.log('⚠️  کاربر admin از قبل وجود دارد.');
      console.log('   ID:', row.id);
      console.log('   Username:', row.username);
      console.log('   Full Name:', row.full_name);
      console.log('   Role:', row.role);
      console.log('   Active:', row.is_active);
      console.log('\n💡 در حال به‌روزرسانی رمز عبور و تنظیمات...\n');

      await client.query(
        `UPDATE expert_user SET
          password_hash = $1,
          full_name = $2,
          email = $3,
          phone = $4,
          role = $5,
          is_active = $6
        WHERE username = $7`,
        [
          password_hash,
          ADMIN.full_name,
          ADMIN.email,
          ADMIN.phone,
          ADMIN.role,
          ADMIN.is_active,
          ADMIN.username,
        ]
      );

      console.log('✅ رمز عبور و تنظیمات کاربر admin به‌روزرسانی شد.');
    } else {
      console.log('➕ در حال ایجاد کاربر admin...\n');

      const nextId = await client.query(
        `SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM expert_user`
      );
      const id = nextId.rows[0].next_id;

      await client.query(
        `INSERT INTO expert_user (
          id, username, password_hash, full_name, email, phone,
          role, is_active, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        [
          id,
          ADMIN.username,
          password_hash,
          ADMIN.full_name,
          ADMIN.email,
          ADMIN.phone,
          ADMIN.role,
          ADMIN.is_active,
          now,
        ]
      );

      console.log('✅ کاربر admin با موفقیت ایجاد شد.');
      console.log('   ID:', id);
    }

    // Verify: read back and show
    const verify = await client.query(
      `SELECT id, username, full_name, email, role, is_active,
              LEFT(password_hash::text, 30) AS hash_preview, created_at
       FROM expert_user WHERE username = $1`,
      [ADMIN.username]
    );

    if (verify.rows.length > 0) {
      const r = verify.rows[0];
      console.log('\n============================================================');
      console.log('📋 تأیید ثبت در دیتابیس:');
      console.log('============================================================');
      console.log('   ID:         ', r.id);
      console.log('   Username:   ', r.username);
      console.log('   Full Name:  ', r.full_name);
      console.log('   Email:      ', r.email);
      console.log('   Role:       ', r.role);
      console.log('   is_active:  ', r.is_active);
      console.log('   hash:       ', r.hash_preview + '...');
      console.log('   created_at: ', r.created_at);
      console.log('============================================================');
      console.log('\n🔑 اطلاعات ورود:');
      console.log('   Username: admin');
      console.log('');
    }
  } catch (err) {
    console.error('❌ خطا:', err.message);
    if (err.code) console.error('   Code:', err.code);
    process.exit(1);
  } finally {
    await client.end();
  }
}

main();
