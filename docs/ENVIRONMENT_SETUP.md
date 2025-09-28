# راهنمای تنظیم متغیرهای محیطی

این مستند راهنمای کامل تنظیم متغیرهای محیطی برای پروژه Forwarder است.

## مشکل متداول

هر بار که برنامه را دوباره اجرا می‌کنید، ممکن است با خطاهای زیر مواجه شوید:
- `VITE_API_URL is not defined`
- `CORS policy error`
- مشکلات اتصال به API

## راه حل خودکار

برای حل این مشکلات، اسکریپت خودکار راه‌اندازی ایجاد شده است:

```bash
# اجرای اسکریپت تنظیم محیط
npm run setup:env
```

## تنظیم دستی

### 1. ایجاد فایل `.env`

در ریشه پروژه فایل `.env` ایجاد کنید:

```env
# ===========================================
# FRONTEND ENVIRONMENT VARIABLES (Vite)
# ===========================================
VITE_API_URL=http://127.0.0.1:5000
VITE_APP_NAME=Forwarder App
VITE_APP_VERSION=1.0.0

# ===========================================
# BACKEND ENVIRONMENT VARIABLES (Flask)
# ===========================================

# Database Configuration
DATABASE_URL=postgresql+psycopg2://postgres:bagheri13@127.0.0.1:5432/forwarder_db

# CORS Configuration - Allow multiple origins for development
CORS_ORIGIN=http://localhost:8107,http://localhost:8080,http://localhost:3000,http://127.0.0.1:8107,http://127.0.0.1:8080

# SLA Configuration
SLA_HOURS=2

# Security Configuration
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Development Configuration
FLASK_ENV=development
FLASK_DEBUG=true

# Logging Configuration
LOG_LEVEL=INFO
```

### 2. متغیرهای مهم

#### Frontend (Vite)
- `VITE_API_URL`: آدرس API بک‌اند (پیش‌فرض: http://127.0.0.1:5000)

#### Backend (Flask)
- `DATABASE_URL`: آدرس دیتابیس PostgreSQL
- `CORS_ORIGIN`: لیست پورت‌های مجاز برای CORS
- `SLA_HOURS`: مدت زمان SLA به ساعت

### 3. اعتبارسنجی خودکار

سیستم اعتبارسنجی خودکار در `src/lib/env.ts` پیاده‌سازی شده که:
- متغیرهای ضروری را بررسی می‌کند
- در صورت نبود متغیرها، خطای واضح نمایش می‌دهد
- در کنسول وضعیت محیط را گزارش می‌کند

## راه‌اندازی کامل پروژه

### 1. نصب وابستگی‌ها
```bash
npm install
```

### 2. تنظیم محیط
```bash
npm run setup:env
```

### 3. راه‌اندازی بک‌اند
```bash
# در ترمینال اول
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:FLASK_APP = "backend.wsgi"
$env:FLASK_ENV = "development"
flask run
```

### 4. راه‌اندازی فرانت‌اند
```bash
# در ترمینال دوم
npm run dev
```

## عیب‌یابی

### خطای CORS
اگر با خطای CORS مواجه شدید:
1. مطمئن شوید پورت فرانت‌اند در `CORS_ORIGIN` موجود است
2. بک‌اند را دوباره راه‌اندازی کنید

### خطای API URL
اگر با خطای `VITE_API_URL is not defined` مواجه شدید:
1. فایل `.env` را بررسی کنید
2. `npm run setup:env` را اجرا کنید
3. فرانت‌اند را دوباره راه‌اندازی کنید

### پورت‌های مختلف
اگر از پورت‌های مختلف استفاده می‌کنید، آنها را به `CORS_ORIGIN` اضافه کنید:
```env
CORS_ORIGIN=http://localhost:8107,http://localhost:8080,http://localhost:3000
```

## نکات مهم

1. **هرگز فایل `.env` را در Git commit نکنید**
2. **در production، همه کلیدهای امنیتی را تغییر دهید**
3. **برای هر محیط، فایل `.env` جداگانه ایجاد کنید**
4. **پورت‌های CORS را فقط به نیازهای خود محدود کنید**

## پشتیبانی

در صورت بروز مشکل:
1. کنسول مرورگر را بررسی کنید
2. لاگ‌های بک‌اند را بررسی کنید
3. فایل `.env` را با این مستند مقایسه کنید

