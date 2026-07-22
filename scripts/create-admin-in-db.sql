-- Create admin user in expert_user table
-- Uses pgcrypto for bcrypt-compatible password hash (Pirooz13@!)
-- Run: psql -h 127.0.0.1 -U postgres -d forwarder_db -f scripts/create-admin-in-db.sql
-- Or: PGPASSWORD=change_me psql -h 127.0.0.1 -U postgres -d forwarder_db -f scripts/create-admin-in-db.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- If admin already exists, update password and settings first
UPDATE expert_user
SET
  password_hash = crypt('Pirooz13@!', gen_salt('bf')),
  full_name = 'مدیر سیستم',
  email = 'admin@company.com',
  phone = '09120000000',
  role = 'admin',
  is_active = true
WHERE username = 'admin';

-- If admin does not exist, insert (id = max(id)+1)
INSERT INTO expert_user (
  id,
  username,
  password_hash,
  full_name,
  email,
  phone,
  role,
  is_active,
  created_at
)
SELECT
  (SELECT COALESCE(MAX(id), 0) + 1 FROM expert_user),
  'admin',
  crypt('Pirooz13@!', gen_salt('bf')),
  'مدیر سیستم',
  'admin@company.com',
  '09120000000',
  'admin',
  true,
  NOW()
WHERE NOT EXISTS (SELECT 1 FROM expert_user WHERE username = 'admin');

-- Verify
SELECT id, username, full_name, role, is_active,
       LEFT(password_hash, 20) AS hash_preview,
       created_at
FROM expert_user
WHERE username = 'admin';
