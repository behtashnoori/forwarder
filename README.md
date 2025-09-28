# پروژه Forwarder - سیستم مدیریت درخواست‌های حمل

## توضیحات پروژه

این پروژه یک سیستم کامل برای مدیریت درخواست‌های حمل و نقل است که شامل:
- **فرانت‌اند**: React + TypeScript + Vite
- **بک‌اند**: Flask + Python
- **دیتابیس**: PostgreSQL
- **مدیریت**: Docker

## پیش‌نیازها

- Docker و Docker Compose نصب شده باشد
- دسترسی administrator/root
- پورت‌های 80 و 8080 آزاد باشد

## راه‌اندازی سریع

### 1. دانلود و استخراج پروژه
```bash
# دانلود فایل پروژه و استخراج
unzip forwarder-project.zip
cd forwarder-project
```

### 2. تنظیم محیط
```bash
# اجرای اسکریپت تنظیم
chmod +x setup-env.sh
./setup-env.sh
```

### 3. تنظیم متغیرهای محیطی
```bash
# ویرایش تنظیمات production
nano backend/.env.production

# تغییر موارد زیر:
# - SECRET_KEY: کلید امنیتی جدید
# - CORS_ORIGIN: دامنه وب‌سایت شما
```

### 4. تنظیم رمز عبور دیتابیس
```bash
# تنظیم رمز عبور دیتابیس
export DB_PASSWORD="your-secure-database-password"
```

### 5. راه‌اندازی پروژه
```bash
# اجرای deployment
./deploy.sh
```

## دسترسی‌ها

- **وب‌سایت اصلی**: http://your-server-ip/
- **پنل مدیریت دیتابیس**: http://your-server-ip:8080
- **لاگ‌های سیستم**: ./instance/logs/

## مدیریت پروژه

### مشاهده وضعیت سرویس‌ها
```bash
docker-compose -f docker-compose.production.yml ps
```

### مشاهده لاگ‌ها
```bash
# لاگ API
docker-compose -f docker-compose.production.yml logs -f api

# لاگ دیتابیس
docker-compose -f docker-compose.production.yml logs -f db
```

### پشتیبان‌گیری از دیتابیس
```bash
docker-compose -f docker-compose.production.yml exec db pg_dump -U postgres forwarder_db > backup/db_backup_$(date +%Y%m%d_%H%M%S).sql
```

### به‌روزرسانی پروژه
```bash
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

در صورت بروز مشکل:
1. لاگ‌ها رو بررسی کنید
2. وضعیت سرویس‌ها رو چک کنید
3. با تیم پشتیبانی تماس بگیرید

## فایل‌های مهم

- `DEPLOYMENT.md`: راهنمای کامل نصب و راه‌اندازی
- `docker-compose.production.yml`: تنظیمات Docker
- `backend/.env.production`: تنظیمات محیطی
- `deploy.sh`: اسکریپت deployment
- `setup-env.sh`: اسکریپت تنظیم محیط

## تکنولوژی‌های استفاده شده

این پروژه با استفاده از تکنولوژی‌های زیر ساخته شده:

- **Frontend**: Vite, TypeScript, React, shadcn-ui, Tailwind CSS
- **Backend**: Flask, Python, SQLAlchemy
- **Database**: PostgreSQL
- **Containerization**: Docker, Docker Compose
- **Deployment**: Gunicorn, Nginx (optional)
