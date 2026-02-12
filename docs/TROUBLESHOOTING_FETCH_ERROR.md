# راهنمای عیب‌یابی خطای "Failed to fetch"

## مشکل: خطای "خطا در دریافت استان‌ها" / "Failed to fetch"

وقتی از اینترنت به اپ دسترسی دارید اما درخواست‌های API خطا می‌دهند.

---

## مراحل عیب‌یابی

### 1️⃣ بررسی اجرای بک‌اند

**مطمئن شوید بک‌اند در حال اجرا است:**

```powershell
# در PowerShell
python backend/wsgi.py
```

**باید این پیام را ببینید:**
```
 * Running on http://0.0.0.0:5000
```

⚠️ **مهم:** اگر می‌بینید `Running on http://127.0.0.1:5000` یعنی بک‌اند فقط روی localhost گوش می‌دهد و از شبکه قابل دسترسی نیست.

**راه‌حل:** متغیر محیطی را تنظیم کنید:
```powershell
$env:FLASK_RUN_HOST="0.0.0.0"
python backend/wsgi.py
```

یا در فایل `.env` اضافه کنید:
```
FLASK_RUN_HOST=0.0.0.0
```

---

### 2️⃣ تست اتصال به بک‌اند

**از خود سرور تست کنید:**

```powershell
# تست از localhost
Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health"

# تست از IP شبکه
Invoke-WebRequest -Uri "http://130.185.77.25:5000/api/health"
```

اگر اولی کار کرد ولی دومی نه، یعنی بک‌اند روی `0.0.0.0` گوش نمی‌دهد.

**تست endpoint استان‌ها:**
```powershell
Invoke-WebRequest -Uri "http://130.185.77.25:5000/api/provinces"
```

---

### 3️⃣ بررسی فایروال ویندوز

**بررسی قوانین فایروال:**

```powershell
Get-NetFirewallRule -DisplayName "*5000*" | Select-Object DisplayName, Enabled, Direction
Get-NetFirewallRule -DisplayName "*8080*" | Select-Object DisplayName, Enabled, Direction
```

**اگر قانون وجود ندارد یا غیرفعال است:**

```powershell
npm run firewall:open
```

یا دستی:
```powershell
New-NetFirewallRule -DisplayName "Flask API - Port 5000" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

---

### 4️⃣ بررسی Console مرورگر

**در مرورگر (F12 → Console) بررسی کنید:**

1. **API URL که استفاده می‌شود:**
   - باید `http://130.185.77.25:5000` باشد نه `http://127.0.0.1:5000`
   - اگر `127.0.0.1` است، یعنی کد قدیمی در مرورگر cache شده

2. **خطاهای CORS:**
   - اگر خطای CORS می‌بینید، بک‌اند را ریستارت کنید تا تنظیمات CORS جدید اعمال شود

**راه‌حل Cache:**
- Hard Refresh: `Ctrl + Shift + R` یا `Ctrl + F5`
- Clear Cache: F12 → Application → Clear Storage → Clear site data

---

### 5️⃣ بررسی Network Tab

**در مرورگر (F12 → Network):**

1. صفحه را Refresh کنید
2. به دنبال درخواست `/api/provinces` بگردید
3. روی آن کلیک کنید و بررسی کنید:
   - **Request URL:** باید `http://130.185.77.25:5000/api/provinces` باشد
   - **Status:** اگر `(failed)` یا `CORS error` است، مشکل از CORS یا فایروال است
   - **Response:** اگر `Failed to fetch` است، احتمالاً بک‌اند در دسترس نیست

---

### 6️⃣ اجرای اسکریپت تست

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test-backend-connection.ps1
```

این اسکریپت همه موارد بالا را بررسی می‌کند.

---

## راه‌حل‌های سریع

### اگر بک‌اند در حال اجرا نیست:
```powershell
python backend/wsgi.py
```

### اگر بک‌اند روی 127.0.0.1 اجرا شده:
```powershell
$env:FLASK_RUN_HOST="0.0.0.0"
python backend/wsgi.py
```

### اگر فایروال بسته است:
```powershell
npm run firewall:open
```

### اگر Cache مرورگر مشکل دارد:
- Hard Refresh: `Ctrl + Shift + R`
- یا مرورگر را ببندید و دوباره باز کنید

### اگر هنوز کار نمی‌کند:
1. بک‌اند را متوقف کنید (Ctrl+C)
2. دوباره با `FLASK_RUN_HOST=0.0.0.0` اجرا کنید
3. مرورگر را Hard Refresh کنید
4. از Network Tab بررسی کنید که درخواست به IP درست می‌رود

---

## بررسی نهایی

بعد از انجام مراحل بالا، این تست‌ها را انجام دهید:

1. ✅ بک‌اند روی `0.0.0.0:5000` در حال اجرا است
2. ✅ فایروال پورت 5000 را باز کرده است
3. ✅ از مرورگر به `http://130.185.77.25:5000/api/health` می‌رسید
4. ✅ در Console مرورگر API URL درست است (`http://130.185.77.25:5000`)
5. ✅ در Network Tab درخواست‌ها به IP درست می‌روند

اگر همه این‌ها درست است ولی هنوز خطا می‌دهد، احتمالاً مشکل از **فایروال یا روتر بیرون از این ویندوز** است که پورت 5000 را بسته است.
