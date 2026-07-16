# سخت‌سازی چرخه توکن و Logout

## 1. ریسک فعلی
پیش از این تغییر، logout فقط توکن مرورگر را حذف می‌کرد و bearer صادرشده تا انقضا معتبر می‌ماند.

## 2. چرخه access-token
ورود، access و refresh جداگانه می‌سازد. access یک ساعت و refresh سی روز اعتبار پیش‌فرض دارد و PyJWT امضا و `exp` را کنترل می‌کند.

## 3. jti
هر توکن یک UUID تصادفی و یکتا دارد. توکن‌های قدیمی بدون `jti` به‌صورت fail-closed رد می‌شوند.

## 4. رفتار Logout
`POST /api/expert/auth/logout` نشست منطقی متعلق به access-token ارائه‌شده را لغو می‌کند؛ access و refresh همان نشست دیگر معتبر نیستند و نشست مستقل باقی می‌ماند. تکرار درخواست نتیجه کنترل‌شده 401 دارد.

## 5. ذخیره لغو
جدول `revoked_token` شامل jti، کاربر، نوع، دلیل و زمان‌هاست؛ lookup بر jti index و unique است.

## 6. منع raw token
توکن خام، رمز یا hash در جدول revocation یا log ذخیره نمی‌شود.

## 7. انقضا
رکورد لغو تا `exp` نگه داشته می‌شود.

## 8. Cleanup
`python scripts/cleanup_revoked_tokens.py` خشک‌اجراست؛ `--apply` فقط رکوردهای منقضی را حذف می‌کند. اجرای روزانه پیشنهاد می‌شود.

## 9. غیرفعال‌سازی حساب
مسیر مرکزی احراز هویت در هر درخواست وجود و active بودن کاربر را کنترل می‌کند.

## 10. تغییر رمز
تغییر موفق رمز تمام نشست‌های فعال کاربر هدف را با دلیل `password_changed` در همان transaction لغو می‌کند.

## 11. پاسخ API
قرارداد login/refresh/logout حفظ شده و خطاهای token با 401 کنترل‌شده برمی‌گردند؛ نقش ناکافی 403 باقی می‌ماند.

## 12. رفتار Frontend
frontend ابتدا logout سرور را فراخوانی می‌کند و حتی در شکست شبکه، state محلی را پاک و به ورود هدایت می‌کند.

## 13. Browser UAT
ورود، logout، redirect مسیر محافظت‌شده و رد token لغوشده باید در محیط disposable بررسی شوند.

## 14. Migration
revision `20260718_add_token_revocation` پس از head گمرک قرار دارد و فقط جدول و indexهای revocation را می‌سازد.

## 15. Rollback
downgrade جدول revocation را حذف می‌کند؛ در این حالت لغوهای ثبت‌شده از بین می‌روند.

## 16. Monitoring
فقط شمار aggregate cleanup و نرخ پاسخ‌های 401 پایش شود؛ jti و bearer ثبت نشود.

## 17. محدودیت‌های امنیتی
نشست‌های صادرشده پیش از migration فاقد `sid` هستند و عمداً fail-closed می‌شوند؛ کاربران باید دوباره وارد شوند. endpoint اجباری برای logout کاربر دیگر اضافه نشده است، زیرا سیاست فعلی مدیریت کاربران audit مستقل لازم برای آن را ندارد.
## 18. AuthSession و Refresh Rotation
هر login یک `AuthSession` با شناسه opaque می‌سازد. access و refresh دارای `sid` مشترک و `jti` مستقل هستند. refresh موفق، JTI قبلی را مصرف و یک جفت token جدید صادر می‌کند. استفاده دوباره از refresh مصرف‌شده به‌عنوان replay تلقی و فقط همان نشست را لغو می‌کند.

هیچ access-token یا refresh-token خام و هیچ token hash در پایگاه داده ذخیره نمی‌شود. امضای JWT، `sid` و JTI جاری نشست verifier کافی را فراهم می‌کنند.

## 19. چرخه حساب
`logout-all` تمام نشست‌های فعال کاربر جاری را می‌بندد. تغییر رمز، غیرفعال‌سازی حساب و تغییر نقش مدیریتی نیز نشست‌های فعال کاربر هدف را در همان transaction لغو می‌کنند. حذف کاربر به‌دلیل FK با `ON DELETE CASCADE` نشست‌ها را حذف می‌کند و tokenهای قبلی fail-closed می‌شوند.

## 20. Frontend
frontend هر دو token را نگه می‌دارد، refresh را به‌صورت single-flight اجرا می‌کند، جفت token چرخیده را با هم جایگزین می‌کند و در شکست refresh تمام state احراز هویت را پاک می‌کند. هر درخواست حداکثر یک‌بار پس از refresh تکرار می‌شود.

## 21. Migration و Cleanup
revision `20260719_add_auth_sessions` جدول نشست و constraintهای lifecycle را اضافه می‌کند. بررسی catalog PostgreSQL ثابت کرد index غیرunique روی `revoked_token.jti` با unique-index constraint تکراری است؛ migration فقط index تکراری را حذف می‌کند و uniqueness حفظ می‌شود.

`python scripts/cleanup_auth_sessions.py` به‌طور پیش‌فرض dry-run است و فقط sessionهای منقضی یا لغوشده‌ی خارج از retention را حذف می‌کند.
