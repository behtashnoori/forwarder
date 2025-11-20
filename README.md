# پروژه Forwarder - سیستم مدیریت درخواست‌های حمل

## توضیحات پروژه

این پروژه یک سیستم کامل برای مدیریت درخواست‌های حمل و نقل است که شامل:
- **فرانت‌اند**: React + TypeScript + Vite
- **بک‌اند**: Flask + Python
- **دیتابیس**: PostgreSQL
- **مدیریت**: Docker

## 🚀 شروع سریع

### 🖥️ روش 1: اجرای محلی (پیشنهادی برای توسعه)

برای شروع کار با پروژه، ابتدا آن را به صورت محلی اجرا کنید:

**📋 پیش‌نیازها:**
- Python 3.12+
- Node.js 18+
- PostgreSQL 16+

**⚡ راه‌اندازی سریع:**
```bash
# 1. نصب وابستگی‌ها
python -m venv .venv
.venv\Scripts\pip install -r backend/requirements.txt   # ویندوز
# یا: source .venv/bin/activate && pip install -r backend/requirements.txt
npm install

# 2. تنظیم دیتابیس
sudo -u postgres psql -c "CREATE DATABASE forwarder_db;"

# 3. اجرای migrations
cd backend && flask db upgrade && cd ..

# 4. اجرای backend (از ریشه پروژه)
.venv\Scripts\python.exe backend\wsgi.py          # ویندوز
# یا: FLASK_RUN_PORT=8501 python backend/wsgi.py  # لینوکس/مک

# 5. اجرای frontend (در ترمینال جدید)
npm run dev -- --port 9960
```

**📖 راهنمای کامل:** [local_setup.md](local_setup.md)

### 🐳 روش 2: اجرای با Docker

برای deployment در سرور:

**📋 پیش‌نیازها:**
- Docker و Docker Compose
- دسترسی administrator/root
- پورت‌های 80 و 8080 آزاد

**⚡ راه‌اندازی سریع:**
```bash
# 1. تنظیم محیط
chmod +x setup-env.sh && ./setup-env.sh

# 2. تنظیم متغیرهای محیطی
cp backend/env.production.example backend/.env.production
nano backend/.env.production

# 3. تنظیم رمز عبور دیتابیس
export DB_PASSWORD="your-secure-database-password"

# 4. راه‌اندازی
./deploy.sh
```

**📖 راهنمای کامل:** [DEPLOYMENT.md](DEPLOYMENT.md)

## 🔗 دسترسی‌ها

### اجرای محلی
- **Frontend (Vite dev server)**: http://localhost:9960
- **Backend API (Flask dev server)**: http://127.0.0.1:8501
- **API Health**: http://127.0.0.1:8501/api/health

### اجرای Docker
- **وب‌سایت اصلی**: http://your-server-ip/
- **پنل مدیریت دیتابیس**: http://your-server-ip:8080
- **لاگ‌های سیستم**: ./instance/logs/

## 📚 مستندات و راهنماها

| فایل | توضیحات |
|------|---------|
| **[local_setup.md](local_setup.md)** | 🖥️ راهنمای کامل اجرای محلی |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | 🐳 راهنمای deployment با Docker |
| **[DOCKER_README.md](DOCKER_README.md)** | 📖 راهنمای Docker و Containerization |
| **[docs/API.md](docs/API.md)** | 🔌 مستندات API |
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | 👤 راهنمای کاربر |
| **[docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)** | 🏗️ معماری سیستم |

## تکنولوژی‌های استفاده شده

این پروژه با استفاده از تکنولوژی‌های زیر ساخته شده:

- **Frontend**: Vite, TypeScript, React, shadcn-ui, Tailwind CSS
- **Backend**: Flask, Python, SQLAlchemy
- **Database**: PostgreSQL
- **Containerization**: Docker, Docker Compose
- **Deployment**: Gunicorn, Nginx (optional)
