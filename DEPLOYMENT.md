# راهنمای نصب و راه‌اندازی پروژه Forwarder

## پیش‌نیازها

- Docker و Docker Compose نصب شده باشد
- دسترسی root یا administrator

## مراحل نصب

### 1. کپی کردن فایل‌ها
```bash
# کپی کردن تمام فایل‌های پروژه به سرور
scp -r . user@server:/path/to/project/
```

### 2. تنظیم متغیرهای محیطی
```bash
# کپی کردن فایل نمونه و ویرایش آن
cp backend/env.production.example backend/.env.production
nano backend/.env.production

# تغییر موارد زیر:
# - SECRET_KEY: کلید امنیتی جدید
# - CORS_ORIGIN: دامنه وب‌سایت
# - DB_PASSWORD: رمز عبور دیتابیس (متغیر محیطی)
```

### 3. تنظیم متغیر محیطی DB_PASSWORD
```bash
# تنظیم رمز عبور دیتابیس
export DB_PASSWORD="your-secure-database-password"
```

### 4. راه‌اندازی
```bash
# اجرای اسکریپت deployment
chmod +x deploy.sh
./deploy.sh
```

### 5. بررسی وضعیت
```bash
# مشاهده وضعیت سرویس‌ها
docker-compose -f docker-compose.production.yml ps

# مشاهده لاگ‌ها
docker-compose -f docker-compose.production.yml logs -f api
```

## دسترسی‌ها

- **وب‌سایت**: http://server-ip/
- **پنل مدیریت دیتابیس**: http://server-ip:8080
- **لاگ‌ها**: ./instance/logs/

## پشتیبان‌گیری

```bash
# پشتیبان‌گیری از دیتابیس
docker-compose -f docker-compose.production.yml exec db pg_dump -U postgres forwarder_db > backup/db_backup_$(date +%Y%m%d_%H%M%S).sql
```

## به‌روزرسانی

```bash
# به‌روزرسانی پروژه
git pull
./deploy.sh
```

## عیب‌یابی

### مشکل اتصال به دیتابیس
```bash
# بررسی وضعیت دیتابیس
docker-compose -f docker-compose.production.yml logs db

# تست اتصال
docker-compose -f docker-compose.production.yml exec api python -c "from backend import create_app; app = create_app(); print('Database connection OK')"
```

### مشکل پورت
```bash
# بررسی پورت‌های در حال استفاده
netstat -tulpn | grep :80
netstat -tulpn | grep :8080
```

## تنظیمات امنیتی

1. **تغییر SECRET_KEY**: حتماً کلید مخفی رو تغییر بدید
2. **محدود کردن CORS_ORIGIN**: فقط دامنه‌های مجاز رو اجازه بدید
3. **فایروال**: پورت 8080 (Adminer) رو فقط برای IP های مجاز باز کنید
4. **رمز عبور دیتابیس**: از رمز عبور قوی استفاده کنید

## پشتیبانی

در صورت بروز مشکل، لاگ‌ها رو بررسی کنید:
```bash
# لاگ API
docker-compose -f docker-compose.production.yml logs api

# لاگ دیتابیس
docker-compose -f docker-compose.production.yml logs db
```
