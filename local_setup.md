# 🖥️ راهنمای اجرای محلی پروژه Forwarder

این راهنما برای اجرای پروژه به صورت محلی بدون استفاده از Docker است.

> **💡 نکته مهم**: قبل از استفاده از Docker، پیشنهاد می‌شود ابتدا پروژه را به صورت محلی اجرا کنید تا با ساختار و عملکرد آن آشنا شوید.

## 📋 پیش‌نیازها

- **Python**: 3.12 یا بالاتر
- **Node.js**: 18 یا بالاتر  
- **PostgreSQL**: 16 یا بالاتر
- **npm**: برای مدیریت dependencies
- **pip**: برای نصب Python packages

## 🚀 مرحله 1: نصب Dependencies

### Frontend Dependencies
```bash
npm install
```

### Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
cd ..
```

## 🗄️ مرحله 2: تنظیم PostgreSQL

### نصب PostgreSQL (اگر نصب نیست)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**Windows:**
- از [postgresql.org](https://www.postgresql.org/download/windows/) دانلود کنید

**macOS:**
```bash
brew install postgresql
```

### ایجاد دیتابیس
```bash
# ورود به PostgreSQL
sudo -u postgres psql

# ایجاد دیتابیس
CREATE DATABASE forwarder_db;

# خروج
\q
```

### تنظیمات پیش‌فرض
پروژه با این تنظیمات پیش‌فرض کار می‌کند:
- **Host**: 127.0.0.1
- **Port**: 5432
- **Username**: postgres
- **Password**: change_me
- **Database**: forwarder_db

### تغییر تنظیمات (در صورت نیاز)
اگر تنظیمات شما متفاوت است، فایل `backend/__init__.py` را ویرایش کنید:

```python
"SQLALCHEMY_DATABASE_URI": os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://forwarder_dev:change_me@localhost:5432/forwarder_dev",
),
```

## 🔄 مرحله 3: اجرای Database Migrations

```bash
cd backend
flask db upgrade
cd ..
```

## 🌱 مرحله 4: Seed داده‌های اولیه (اختیاری)

```bash
python manage.py create-admin
```

The command prompts securely for an operator-selected password. Shared sample users and executable default credentials are not created. Additional users must be created individually through the authorized administration flow.

## 🖥️ مرحله 5: اجرای Backend

**روش 1: اجرای مستقیم (پیشنهادی)**
```bash
# از root پروژه
python backend/wsgi.py
```

**روش 2: اجرای از پوشه backend**
```bash
cd backend
python wsgi.py
```

Backend روی `http://localhost:5000` اجرا می‌شود.

**تأیید اجرا:**
- در مرورگر به `http://localhost:5000` بروید
- باید پیام "✅ Backend is running" را ببینید

## 🌐 مرحله 6: اجرای Frontend

در یک **ترمینال جدید** (backend باید در حال اجرا باشد):

```bash
npm run dev
```

Frontend روی `http://localhost:5173` اجرا می‌شود.

**تأیید اجرا:**
- در مرورگر به `http://localhost:5173` بروید
- باید صفحه اصلی پروژه را ببینید

## 🔗 دسترسی‌ها

| سرویس | URL | توضیحات |
|--------|-----|---------|
| **Frontend** | http://localhost:5173 | رابط کاربری اصلی |
| **Backend API** | http://localhost:5000 | API endpoints |
| **API Health** | http://localhost:5000/api/health | بررسی وضعیت API |

## 🐛 عیب‌یابی

### خطای اتصال به دیتابیس

**بررسی وضعیت PostgreSQL:**
```bash
# Linux/macOS
sudo systemctl status postgresql

# راه‌اندازی در صورت توقف
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Windows:**
```bash
# بررسی سرویس PostgreSQL
services.msc
```

**تست اتصال:**
```bash
psql -h 127.0.0.1 -U postgres -d forwarder_db
```

### خطای Port در حال استفاده

**پیدا کردن پروسس:**
```bash
# Linux/macOS
lsof -i :5000
lsof -i :5173

# Windows
netstat -ano | findstr :5000
netstat -ano | findstr :5173
```

**تغییر پورت Frontend:**
فایل `vite.config.ts` را ویرایش کنید:
```typescript
server: {
  port: 3000, // تغییر از 5173 به 3000
}
```

### خطای Migration

**بازنشانی migrations:**
```bash
cd backend
flask db downgrade base
flask db upgrade
cd ..
```

### خطای Dependencies

**پاک کردن و نصب مجدد:**
```bash
# Frontend
rm -rf node_modules package-lock.json
npm install

# Backend
pip install --upgrade pip
pip install -r backend/requirements.txt --force-reinstall
```

## 🛠️ دستورات مفید

### تست API
```bash
npm run test:api
```

### Lint کردن کد
```bash
npm run lint
```

### Build کردن Frontend
```bash
npm run build
```

### مشاهده API endpoints
```bash
curl http://localhost:5000/api/health
```

## 📁 ساختار پروژه

```
forwarder/
├── src/                 # Frontend React
├── backend/            # Backend Flask
├── docs/              # مستندات
├── package.json       # Frontend dependencies
├── requirements.txt   # Backend dependencies
└── README.md         # راهنمای اصلی
```

## 🔧 تنظیمات پیشرفته

### متغیرهای محیطی
می‌توانید فایل `.env` در root پروژه ایجاد کنید:

```bash
# .env
DATABASE_URL=postgresql+psycopg2://forwarder_dev:change_me@localhost:5432/forwarder_dev
CORS_ORIGIN=http://localhost:5173
SECRET_KEY=your-secret-key
FLASK_ENV=development
FLASK_DEBUG=True
```

### تنظیمات IDE
برای VS Code، فایل `.vscode/settings.json` ایجاد کنید:

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "typescript.preferences.includePackageJsonAutoImports": "auto"
}
```

## 📞 پشتیبانی

در صورت بروز مشکل:

1. **لاگ‌های خطا را بررسی کنید**
2. **وضعیت سرویس‌ها را چک کنید**
3. **مستندات API را مطالعه کنید** (`docs/API.md`)
4. **با تیم پشتیبانی تماس بگیرید**

## 📚 مستندات بیشتر

- [API Documentation](docs/API.md)
- [User Guide](docs/USER_GUIDE.md)
- [System Architecture](docs/SYSTEM_ARCHITECTURE.md)
- [Docker Guide](DOCKER_README.md)

---

## 🐳 مرحله بعدی: Docker

پس از آشنایی با اجرای محلی، می‌توانید از راهنماهای زیر برای deployment با Docker استفاده کنید:

- **[DEPLOYMENT.md](DEPLOYMENT.md)**: راهنمای کامل deployment با Docker
- **[DOCKER_README.md](DOCKER_README.md)**: راهنمای Docker و Containerization
- **[README.md](README.md)**: راهنمای کلی پروژه
