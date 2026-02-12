# راهنمای گام‌به‌گام رفع خطای "خطا در دریافت استان‌ها"

## ⚠️ مهم: این مراحل را به ترتیب انجام دهید

---

## مرحله 1: توقف بک‌اند

در ترمینالی که بک‌اند در حال اجراست:
- `Ctrl + C` بزنید تا متوقف شود

---

## مرحله 2: تنظیم CORS برای دسترسی از شبکه

در فایل `.env` یکی از این دو را داشته باشید:

- `FLASK_ENV=development` یا `FLASK_DEBUG=true`
- یا `CORS_ALLOW_ALL_ORIGINS=1`

بدون یکی از این‌ها، origin مربوط به IP سرور (مثلاً `http://130.185.77.25:8080`) مجاز نیست و CORS خطا می‌دهد.

## مرحله 3: بررسی تغییرات کد

مطمئن شوید که تغییرات CORS اعمال شده است. فایل `backend/routes/locations.py` باید این کد را داشته باشد:

```python
# خط 39 - باید این باشد:
cors_origin = origin if origin else None

# نه این:
# cors_origin = origin if origin in allowed_origins else '*'  # ❌ اشتباه
```

---

## مرحله 4: راه‌اندازی مجدد بک‌اند

```powershell
python backend/wsgi.py
```

**باید این پیام را ببینید:**
```
* Running on all addresses (0.0.0.0)
* Running on http://127.0.0.1:5000
* Running on http://130.185.77.25:5000
```

⚠️ اگر `127.0.0.1` می‌بینید ولی `130.185.77.25` نمی‌بینید، یعنی روی `0.0.0.0` گوش نمی‌دهد.

---

## مرحله 5: تست از PowerShell

در یک **ترمینال جدید** PowerShell:

```powershell
npm run test:provinces
```

این اسکریپت:
- درخواست OPTIONS (CORS preflight) را تست می‌کند
- درخواست GET (داده‌های واقعی) را تست می‌کند
- CORS headers را بررسی می‌کند

**اگر تست موفق بود:**
- باید لیست استان‌ها را ببینید
- CORS headers باید origin واقعی را نشان دهند (نه `*`)

**اگر تست ناموفق بود:**
- خطای دقیق را یادداشت کنید
- به مرحله 5 بروید

---

## مرحله 6: بررسی Console مرورگر

1. در مرورگر `F12` بزنید
2. به تب **Console** بروید
3. صفحه را Refresh کنید (`Ctrl + R`)
4. به دنبال خطاها بگردید:
   - `Failed to fetch`
   - `CORS policy`
   - `Access-Control-Allow-Origin`

**اگر خطای CORS می‌بینید:**
- بک‌اند را دوباره ریستارت کنید
- Hard Refresh کنید: `Ctrl + Shift + R`

---

## مرحله 7: بررسی Network Tab

1. در مرورگر `F12` بزنید
2. به تب **Network** بروید
3. صفحه را Refresh کنید
4. به دنبال درخواست `/api/provinces` بگردید
5. روی آن کلیک کنید و بررسی کنید:

**Request Headers:**
- `Origin: http://130.185.77.25:8080` (باید IP سرور باشد)

**Response Headers:**
- `Access-Control-Allow-Origin: http://130.185.77.25:8080` (باید origin واقعی باشد، نه `*`)
- `Access-Control-Allow-Credentials: true`

**Status:**
- باید `200` باشد (نه `(failed)` یا `CORS error`)

---

## مرحله 8: بررسی لاگ بک‌اند

در ترمینال بک‌اند، بعد از Refresh صفحه باید این لاگ‌ها را ببینید:

```
37.32.37.111 - - [12/Feb/2026 11:53:34] "OPTIONS /api/provinces HTTP/1.1" 200 -
37.32.37.111 - - [12/Feb/2026 11:53:34] "GET /api/provinces HTTP/1.1" 200 -
```

**اگر فقط OPTIONS می‌بینید ولی GET نمی‌بینید:**
- یعنی درخواست GET نمی‌رسد یا خطا می‌دهد
- به مرحله 8 بروید

**اگر هیچ کدام را نمی‌بینید:**
- یعنی درخواست‌ها به بک‌اند نمی‌رسند
- فایروال یا روتر بیرونی را بررسی کنید

---

## مرحله 9: بررسی دیتابیس

اگر درخواست GET می‌رسد ولی خطا می‌دهد، ممکن است مشکل از دیتابیس باشد:

```powershell
# تست اتصال به دیتابیس
python -c "from backend import create_app; app = create_app(); app.app_context().push(); from backend.extensions import db; db.session.execute(db.text('SELECT COUNT(*) FROM province'))"
```

**اگر خطا داد:**
- دیتابیس را بررسی کنید
- مطمئن شوید که جدول `province` وجود دارد

---

## مرحله 10: Hard Refresh مرورگر

گاهی cache مرورگر مشکل ایجاد می‌کند:

1. `Ctrl + Shift + Delete` بزنید
2. "Cached images and files" را انتخاب کنید
3. "Clear data" را بزنید
4. یا Hard Refresh: `Ctrl + Shift + R`

---

## مرحله 11: تست مستقیم از مرورگر

در مرورگر، این آدرس را مستقیماً باز کنید:

```
http://130.185.77.25:5000/api/provinces
```

**اگر JSON استان‌ها را می‌بینید:**
- یعنی بک‌اند کار می‌کند
- مشکل از CORS یا فرانت‌اند است

**اگر خطا می‌دهد:**
- مشکل از بک‌اند یا دیتابیس است

---

## خلاصه مشکلات رایج

| مشکل | راه‌حل |
|------|--------|
| فقط OPTIONS می‌آید، GET نمی‌آید | بک‌اند را ریستارت کنید |
| CORS error در Console | Hard Refresh کنید، بک‌اند را ریستارت کنید |
| `Access-Control-Allow-Origin: *` | کد را بررسی کنید، باید origin واقعی باشد |
| `Failed to fetch` | فایروال را بررسی کنید، بک‌اند را چک کنید |
| خطای دیتابیس | دیتابیس را بررسی کنید |

---

## اگر هنوز کار نمی‌کند

1. خروجی `npm run test:provinces` را بفرستید
2. Screenshot از Console مرورگر (F12 → Console)
3. Screenshot از Network Tab (F12 → Network → /api/provinces)
4. لاگ‌های بک‌اند (آخرین 10 خط)
