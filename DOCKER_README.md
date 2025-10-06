# 🐳 راهنمای Docker Deployment

این پروژه کاملاً Dockerized شده و آماده deployment در production است.

## 🚀 نصب سریع

### 1. تنظیم محیط
```bash
# کپی کردن فایل‌های محیطی
chmod +x setup-env.sh
./setup-env.sh

# تنظیم رمز عبور دیتابیس
export DB_PASSWORD="your-secure-database-password"
```

### 2. ویرایش تنظیمات
```bash
# ویرایش فایل محیطی production
nano backend/.env.production

# موارد مهم برای تغییر:
# - SECRET_KEY: کلید امنیتی قوی
# - CORS_ORIGIN: دامنه وب‌سایت شما
```

### 3. اجرای deployment
```bash
chmod +x deploy.sh
./deploy.sh
```

## 🏗️ ساختار سرویس‌ها

### Frontend (React + Vite)
- **پورت**: 80
- **نوع**: Nginx static files
- **Build**: Multi-stage Docker build

### Backend (Flask API)
- **پورت داخلی**: 5000
- **نوع**: Gunicorn WSGI server
- **Health Check**: `/api/health`

### Database (PostgreSQL)
- **پورت داخلی**: 5432
- **نوع**: PostgreSQL 16
- **Admin Panel**: Adminer on port 8080

## 🔧 مدیریت سرویس‌ها

### مشاهده وضعیت
```bash
docker-compose -f docker-compose.production.yml ps
```

### مشاهده لاگ‌ها
```bash
# همه سرویس‌ها
docker-compose -f docker-compose.production.yml logs -f

# فقط API
docker-compose -f docker-compose.production.yml logs -f api

# فقط Frontend
docker-compose -f docker-compose.production.yml logs -f frontend
```

### راه‌اندازی مجدد
```bash
# راه‌اندازی مجدد همه سرویس‌ها
docker-compose -f docker-compose.production.yml restart

# راه‌اندازی مجدد سرویس خاص
docker-compose -f docker-compose.production.yml restart api
```

## 📊 مانیتورینگ

### Health Checks
- **Frontend**: http://your-domain/
- **API**: http://your-domain/api/health
- **Database**: Adminer on port 8080

### Logs
- **API Logs**: `./instance/logs/`
- **Nginx Logs**: داخل container
- **Database Logs**: `docker logs <container-name>`

## 🔄 به‌روزرسانی

```bash
# دریافت آخرین تغییرات
git pull

# rebuild و راه‌اندازی مجدد
./deploy.sh
```

## 🛡️ امنیت

### تنظیمات امنیتی مهم:
1. **SECRET_KEY**: از کلید قوی استفاده کنید
2. **CORS_ORIGIN**: فقط دامنه‌های مجاز را اجازه دهید
3. **DB_PASSWORD**: رمز عبور قوی برای دیتابیس
4. **Firewall**: پورت 8080 (Adminer) را محدود کنید

### پشتیبان‌گیری
```bash
# پشتیبان‌گیری از دیتابیس
docker-compose -f docker-compose.production.yml exec db pg_dump -U postgres forwarder_db > backup/db_backup_$(date +%Y%m%d_%H%M%S).sql
```

## 🐛 عیب‌یابی

### مشکل اتصال API
```bash
# بررسی health check
curl http://localhost/api/health

# بررسی لاگ‌های API
docker-compose -f docker-compose.production.yml logs api
```

### مشکل Frontend
```bash
# بررسی لاگ‌های Nginx
docker-compose -f docker-compose.production.yml logs frontend

# بررسی build
docker-compose -f docker-compose.production.yml build frontend
```

### مشکل دیتابیس
```bash
# بررسی وضعیت دیتابیس
docker-compose -f docker-compose.production.yml logs db

# تست اتصال
docker-compose -f docker-compose.production.yml exec api python -c "from backend import create_app; app = create_app(); print('DB OK')"
```

## 📋 چک‌لیست قبل از تحویل

- [ ] فایل `backend/.env.production` تنظیم شده
- [ ] متغیر `DB_PASSWORD` تنظیم شده
- [ ] `SECRET_KEY` تغییر کرده
- [ ] `CORS_ORIGIN` به دامنه واقعی تنظیم شده
- [ ] تمام سرویس‌ها healthy هستند
- [ ] لاگ‌ها بدون خطا هستند
- [ ] پشتیبان‌گیری از دیتابیس تست شده

## 📞 پشتیبانی

در صورت بروز مشکل:
1. لاگ‌ها را بررسی کنید
2. وضعیت سرویس‌ها را چک کنید
3. با تیم پشتیبانی تماس بگیرید


