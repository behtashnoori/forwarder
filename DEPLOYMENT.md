# 🐳 راهنمای Deployment با Docker - پروژه Forwarder

> **💡 نکته**: این راهنما برای deployment در سرور با Docker است. برای اجرای محلی، ابتدا [local_setup.md](local_setup.md) را مطالعه کنید.

## 📋 پیش‌نیازها

- **Docker**: نسخه 20.10 یا بالاتر
- **Docker Compose**: نسخه 2.0 یا بالاتر  
- **دسترسی**: root یا administrator
- **پورت‌های آزاد**: 80 (HTTP), 8080 (Adminer)

## 🚀 مراحل Deployment

### مرحله 1: آماده‌سازی سرور
```bash
# کپی کردن فایل‌های پروژه به سرور
scp -r . user@server:/path/to/project/
cd /path/to/project/
```

### مرحله 2: تنظیم متغیرهای محیطی
```bash
# کپی کردن فایل نمونه
cp backend/env.production.example backend/.env.production

# ویرایش تنظیمات
nano backend/.env.production
```

**تنظیمات مهم:**
```bash
# در فایل backend/.env.production
SECRET_KEY=your-very-secure-secret-key-here
CORS_ORIGIN=http://your-domain.com
FLASK_ENV=production
FLASK_DEBUG=False
```

### مرحله 3: تنظیم رمز عبور دیتابیس
```bash
# تنظیم متغیر محیطی برای رمز عبور دیتابیس
export DB_PASSWORD="your-secure-database-password"
```

### مرحله 4: راه‌اندازی پروژه
```bash
# اعطای دسترسی اجرا به اسکریپت
chmod +x deploy.sh

# اجرای deployment
./deploy.sh
```

### مرحله 5: بررسی وضعیت
```bash
# مشاهده وضعیت سرویس‌ها
docker-compose -f docker-compose.production.yml ps

# مشاهده لاگ‌های API
docker-compose -f docker-compose.production.yml logs -f api

# مشاهده لاگ‌های دیتابیس
docker-compose -f docker-compose.production.yml logs -f db
```

## 🔗 دسترسی‌ها

| سرویس | URL | توضیحات |
|--------|-----|---------|
| **وب‌سایت اصلی** | http://your-server-ip/ | رابط کاربری Frontend |
| **API Health** | http://your-server-ip/api/health | بررسی وضعیت API |
| **پنل مدیریت DB** | http://your-server-ip:8080 | Adminer برای مدیریت دیتابیس |
| **لاگ‌های سیستم** | ./instance/logs/ | فایل‌های لاگ |

## 🛠️ مدیریت پروژه

### مشاهده وضعیت سرویس‌ها
```bash
# نمایش وضعیت تمام containerها
docker-compose -f docker-compose.production.yml ps

# نمایش جزئیات بیشتر
docker-compose -f docker-compose.production.yml ps -a
```

### مدیریت لاگ‌ها
```bash
# مشاهده لاگ‌های زنده API
docker-compose -f docker-compose.production.yml logs -f api

# مشاهده لاگ‌های دیتابیس
docker-compose -f docker-compose.production.yml logs -f db

# مشاهده لاگ‌های Frontend
docker-compose -f docker-compose.production.yml logs -f frontend
```

### پشتیبان‌گیری از دیتابیس
```bash
# ایجاد پشتیبان از دیتابیس
docker-compose -f docker-compose.production.yml exec db pg_dump -U postgres forwarder_db > backup/db_backup_$(date +%Y%m%d_%H%M%S).sql

# بازگردانی پشتیبان
docker-compose -f docker-compose.production.yml exec -T db psql -U postgres forwarder_db < backup/db_backup_20240101_120000.sql
```

### به‌روزرسانی پروژه
```bash
# دریافت آخرین تغییرات
git pull

# اجرای deployment مجدد
./deploy.sh
```

### راه‌اندازی مجدد سرویس‌ها
```bash
# راه‌اندازی مجدد تمام سرویس‌ها
docker-compose -f docker-compose.production.yml restart

# راه‌اندازی مجدد سرویس خاص
docker-compose -f docker-compose.production.yml restart api
```

## 🐛 عیب‌یابی

### مشکل اتصال به دیتابیس
```bash
# بررسی وضعیت container دیتابیس
docker-compose -f docker-compose.production.yml logs db

# تست اتصال مستقیم
docker-compose -f docker-compose.production.yml exec db psql -U postgres -c "SELECT version();"

# تست اتصال از طریق API
docker-compose -f docker-compose.production.yml exec api python -c "from backend import create_app; app = create_app(); print('Database connection OK')"
```

### مشکل پورت
```bash
# بررسی پورت‌های در حال استفاده
netstat -tulpn | grep :80
netstat -tulpn | grep :8080

# بررسی containerهای در حال اجرا
docker ps | grep forwarder
```

### مشکل Memory یا CPU
```bash
# بررسی استفاده از منابع
docker stats

# پاک کردن containerهای غیرضروری
docker system prune -f
```

### مشکل Build
```bash
# پاک کردن imageهای قدیمی
docker-compose -f docker-compose.production.yml down --rmi all

# Build مجدد
docker-compose -f docker-compose.production.yml build --no-cache
```

## 🔒 تنظیمات امنیتی

### 1. تغییر کلیدهای امنیتی
```bash
# تولید SECRET_KEY جدید
python -c "import secrets; print(secrets.token_hex(32))"

# ویرایش فایل .env.production
nano backend/.env.production
```

### 2. محدود کردن دسترسی‌ها
```bash
# محدود کردن Adminer به IP های خاص
# در docker-compose.production.yml اضافه کنید:
# networks:
#   - internal
#   - external
```

### 3. تنظیم فایروال
```bash
# Ubuntu/Debian
ufw allow 80/tcp
ufw allow 8080/tcp from 192.168.1.0/24  # فقط شبکه داخلی

# CentOS/RHEL
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=8080/tcp --source=192.168.1.0/24
firewall-cmd --reload
```

### 4. رمز عبور قوی دیتابیس
```bash
# تولید رمز عبور قوی
openssl rand -base64 32

# تنظیم متغیر محیطی
export DB_PASSWORD="your-very-strong-password-here"
```

## 📞 پشتیبانی

در صورت بروز مشکل:

1. **بررسی لاگ‌ها:**
```bash
# لاگ‌های کامل سیستم
docker-compose -f docker-compose.production.yml logs

# لاگ‌های سرویس خاص
docker-compose -f docker-compose.production.yml logs api
```

2. **بررسی وضعیت سرویس‌ها:**
```bash
docker-compose -f docker-compose.production.yml ps
```

3. **تست اتصالات:**
```bash
# تست API
curl http://localhost/api/health

# تست دیتابیس
docker-compose -f docker-compose.production.yml exec db pg_isready
```

## 📚 مستندات مرتبط

- **[local_setup.md](local_setup.md)**: راهنمای اجرای محلی
- **[DOCKER_README.md](DOCKER_README.md)**: راهنمای Docker
- **[README.md](README.md)**: راهنمای کلی پروژه
