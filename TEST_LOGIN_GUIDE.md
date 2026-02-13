# راهنمای تست و اصلاح ورود کاربران

## مشکل
کاربران `expert` و `admin` در دیتابیس وجود ندارند یا رمز عبور آنها اشتباه است.

## راه حل

### روش 1: استفاده از اسکریپت fix_users.py (پیشنهادی)

این اسکریپت هر دو کاربر را ایجاد یا اصلاح می‌کند:

```bash
cd c:\1-webapp\1-forwarder
python backend/fix_users.py
```

یا:

```bash
py backend/fix_users.py
```

### روش 2: استفاده از اسکریپت‌های موجود

#### ایجاد کاربر Admin:
```bash
python backend/create_admin.py
```

#### ایجاد کاربر Expert:
```bash
python backend/seed_experts.py
```

**نکته**: اسکریپت `seed_experts.py` فقط در صورتی کاربر ایجاد می‌کند که هیچ کاربری در دیتابیس وجود نداشته باشد.

### روش 3: تست ورود

پس از ایجاد کاربران، می‌توانید با اسکریپت Node.js تست کنید:

```bash
node scripts/test-login-credentials.js
```

## اطلاعات کاربران

### کاربر Expert:
- **Username**: `expert`
- **Password**: `expert123`
- **Role**: `expert`

### کاربر Admin:
- **Username**: `admin`
- **Password**: `Pirooz13@!`
- **Role**: `admin`

## بررسی وضعیت

برای بررسی اینکه کاربران ایجاد شده‌اند:

1. مطمئن شوید backend در حال اجرا است:
   ```bash
   python backend/wsgi.py
   ```

2. تست ورود را اجرا کنید:
   ```bash
   node scripts/test-login-credentials.js
   ```

3. یا مستقیماً از رابط کاربری تست کنید:
   - به `http://localhost:5173` بروید
   - روی "ورود کارشناس" کلیک کنید
   - با اطلاعات بالا وارد شوید

## عیب‌یابی

### مشکل: خطای "ModuleNotFoundError: No module named 'bcrypt'"

**راه حل:**
```bash
pip install -r backend/requirements.txt
```

یا:

```bash
py -m pip install -r backend/requirements.txt
```

### مشکل: خطای اتصال به دیتابیس

**بررسی:**
1. مطمئن شوید PostgreSQL در حال اجرا است
2. بررسی کنید که دیتابیس `forwarder_db` وجود دارد
3. بررسی کنید که اطلاعات اتصال درست است

### مشکل: کاربر ایجاد شد اما نمی‌توانم وارد شوم

**بررسی:**
1. مطمئن شوید کاربر `is_active = True` است
2. بررسی کنید که رمز عبور درست است
3. لاگ‌های backend را بررسی کنید

## تست موفق

اگر همه چیز درست باشد، باید پیام زیر را ببینید:

```
✅ همه تست‌ها موفق بودند!

💡 می‌توانید با این اطلاعات وارد سیستم شوید:
   - کارشناس: expert / expert123
   - مدیر سیستم: admin / Pirooz13@!
```
