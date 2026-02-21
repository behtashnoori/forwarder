# راه‌اندازی محیط توسعه (Dev Setup)

این سند پورت‌های ثابت، دستورهای اجرا و نکات عیب‌یابی را برای محیط توسعه توضیح می‌دهد.

## پورت‌های ثابت

| سرویس   | پورت  | توضیح |
|--------|-------|--------|
| Backend (Flask) | **8000** | همیشه از متغیر `PORT` در `.env` خوانده می‌شود؛ پیش‌فرض ۸۰۰۰. برنامه روی پورت دیگر بالا نمی‌آید. |
| Frontend (Vite) | **8080** | سرور dev فرانت؛ در صورت تمایل از `VITE_DEV_PORT` در env قابل تغییر است. |

## روش اجرا

### ۱) اجرای بک‌اند

از ریشه پروژه (`forwarder/`):

```bash
npm run backend
```

یا مستقیم از پوشه بک‌اند با بارگذاری env:

- **Linux/macOS:** `./backend/start-dev.sh`
- **Windows:** از ریشه پروژه `node scripts/run-backend.js` یا از پوشه backend اجرای `start-dev.bat` (که خودش از ریشه `node scripts/run-backend.js` را صدا می‌زند).

بک‌اند همیشه روی پورت تعیین‌شده در `PORT` (پیش‌فرض ۸۰۰۰) بالا می‌آید.

### ۲) اجرای فرانت

از ریشه پروژه:

```bash
npm run dev
```

درخواست‌های `/api/*` از طریق proxy وایت به بک‌اند (پورت ۸۰۰۰) فرستاده می‌شوند؛ فرانت پورت بک‌اند را مستقیم نمی‌بیند.

## محل فایل‌های env

- **`forwarder/.env`** — متغیرهای اصلی (هم فرانت و هم بک‌اند). این فایل را از روی `.env.example` کپی کنید و مقادیر را تنظیم کنید.
- **`forwarder/.env.example`** — قالب و مستندات متغیرها.

### متغیرهای مهم

| متغیر | کاربرد | پیش‌فرض / نمونه |
|--------|--------|------------------|
| `PORT` | پورت بک‌اند | `8000` |
| `HOST` | host بک‌اند | `0.0.0.0` |
| `CORS_ORIGINS` | originهای مجاز CORS (وقتی فرانت بدون proxy صدا می‌زند) | `http://localhost:5173,http://localhost:8080` |
| `VITE_API_URL` | آدرس API در **production** (برای build فرانت) | در dev لازم نیست؛ در build نهایی ست شود. |
| `VITE_BACKEND_URL` | هدف proxy وایت در dev (اختیاری) | `http://localhost:8000` |
| `DATABASE_URL` | اتصال دیتابیس | طبق `.env.example` |

## اگر پورت اشغال بود

برنامه **خودکار** پورت را عوض نمی‌کند. اگر پورت ۸۰۰۰ (یا هر مقداری که در `PORT` ست کرده‌اید) اشغال باشد، بک‌اند با پیام زیر خارج می‌شود:

```
Port 8000 is in use. Stop the other process or set PORT to another value and restart.
```

**کارهایی که می‌توانید انجام دهید:**

1. **خاموش کردن process روی آن پورت**
   - **Windows (PowerShell):**  
     `Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }`  
     یا با Task Manager process مربوط را ببندید.
   - **Linux/macOS:**  
     `lsof -ti:8000 | xargs kill` یا `kill $(lsof -t -i:8000)`

2. **تغییر دستی پورت:** در `.env` مقدار `PORT` را به پورت دیگری (مثلاً 8001) تغییر دهید و هم‌زمان در فرانت (در dev) اگر بدون proxy تست می‌کنید، `VITE_BACKEND_URL` را با همان پورت تنظیم کنید. در حالت عادی با proxy، فقط بک‌اند را با `PORT` جدید ری‌استارت کنید و مطمئن شوید `VITE_BACKEND_URL` (در صورت استفاده) همان پورت را نشان می‌دهد.

## چک کردن health

- **Endpoint:** `GET /api/health`
- **پاسخ مورد انتظار:** `{"status": "ok", "message": "..."}`

از ترمینال:

```bash
curl http://localhost:8000/api/health
```

در فرانت، در حالت dev یک بار هنگام لود اپ، health به صورت خودکار با `/api/health` (از طریق proxy) چک می‌شود و نتیجه در console مرورگر نمایش داده می‌شود.

## خلاصه

- پورت بک‌اند ثابت است (از env، بدون fallback به پورت دیگر).
- فرانت در dev از proxy استفاده می‌کند و همیشه به `/api` درخواست می‌زند.
- با ری‌استارت‌های متعدد، پورت بک‌اند تغییر نمی‌کند و mismatch بین فرانت و بک‌اند رخ نمی‌دهد.
- توسعه‌دهنده جدید: ابتدا `.env` را از `.env.example` بسازد، سپس `npm run backend` و در ترمینال دیگر `npm run dev`.
