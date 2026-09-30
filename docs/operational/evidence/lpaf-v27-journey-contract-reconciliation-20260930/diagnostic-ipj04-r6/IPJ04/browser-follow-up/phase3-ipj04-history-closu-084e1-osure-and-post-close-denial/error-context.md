# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: phase3-ipj04-history-closure.spec.ts >> FWD-IPJ-04 continues one shared Shipment through history, ETA, privacy, closure, and post-close denial
- Location: e2e\phase3-ipj04-history-closure.spec.ts:109:1

# Error details

```
Error: failed browser requests

expect(received).toEqual(expected) // deep equality

- Expected  - 1
+ Received  + 3

- Array []
+ Array [
+   "GET http://127.0.0.1:57124/api/operational-shipments/24219878-822f-4989-bc87-fc81d2f116e2/route-plans/11/reference-times net::ERR_ABORTED",
+ ]
```

# Page snapshot

```yaml
- generic [ref=f2e2]:
  - region "Notifications (F8)":
    - list
  - region "Notifications alt+T"
  - navigation "ناوبری برنامه" [ref=f2e3]:
    - button "بازگشت" [ref=f2e4] [cursor=pointer]
    - button "خانه" [ref=f2e5] [cursor=pointer]
  - main [ref=f2e6]:
    - link "پرش به محتوای پرونده حمل" [ref=f2e7] [cursor=pointer]:
      - /url: "#shipment-overview"
    - generic [ref=f2e8]:
      - generic [ref=f2e9]:
        - link "← بازگشت به فضای کار امروز" [ref=f2e10] [cursor=pointer]:
          - /url: /operations
        - link "→ بازگشت" [ref=f2e11] [cursor=pointer]:
          - /url: /operations/shipments
      - generic [ref=f2e12]:
        - generic [ref=f2e13]:
          - generic [ref=f2e14]:
            - paragraph [ref=f2e15]: فضای کار عملیاتی محموله
            - heading "خلاصه محموله" [level=1] [ref=f2e16]
            - paragraph [ref=f2e17]: "شناسه محموله: 24219878-822f-4989-bc87-fc81d2f116e2"
          - generic [ref=f2e18]: بسته‌شده
        - generic [ref=f2e19]:
          - generic [ref=f2e20]:
            - paragraph [ref=f2e21]: مشتری و پروژه
            - paragraph [ref=f2e22]: "[SHARED-E2E] Customer A"
            - link "مشاهده پروژه مرتبط" [ref=f2e23] [cursor=pointer]:
              - /url: /operations/projects/725be8e1-c2d5-461f-9b08-5ac07ee82e22/units
          - generic [ref=f2e24]:
            - paragraph [ref=f2e25]: مسئول فعلی پرونده
            - paragraph [ref=f2e26]: "[SHARED-E2E] transfer_target"
            - paragraph [ref=f2e27]: مالکیت از خود محموله خوانده می‌شود.
          - generic [ref=f2e28]:
            - paragraph [ref=f2e29]: مسیر فعال
            - paragraph [ref=f2e30]: تخت قیصر ← الوان
            - paragraph [ref=f2e31]: نسخه 1
          - generic [ref=f2e32]:
            - paragraph [ref=f2e33]: مسیر حمل
            - paragraph [ref=f2e34]: جاده‌ای ← ریلی ← ریلی
          - generic [ref=f2e35]:
            - paragraph [ref=f2e36]: آخرین رخداد عملیاتی
            - paragraph [ref=f2e37]: هنوز رخدادی ثبت نشده
          - generic [ref=f2e38]:
            - paragraph [ref=f2e39]: مرحله فعلی و تازگی پرونده
            - paragraph [ref=f2e40]: مرحله جاری ثبت نشده
            - paragraph [ref=f2e41]: "آخرین تغییر پرونده: ۳۰ سپتامبر ۲۰۲۶ (۸ مهر ۱۴۰۵) · ۱۱:۳۰ (‎+۳:۳۰ گرینویچ)"
          - generic [ref=f2e42]:
            - paragraph [ref=f2e43]: موارد باز
            - paragraph [ref=f2e44]: 2 مورد پیگیری · 0 استثنا
            - paragraph [ref=f2e45]: عملیات مستقیم
      - navigation "عملیات حمل" [ref=f2e46]:
        - link "فضای کار امروز" [ref=f2e47] [cursor=pointer]:
          - /url: /operations
        - link "درخواست‌ها و قیمت‌ها" [ref=f2e48] [cursor=pointer]:
          - /url: /expert
        - link "پرونده‌های عملیاتی حمل" [ref=f2e49] [cursor=pointer]:
          - /url: /operations/shipments
        - link "برج کنترل عملیات" [ref=f2e50] [cursor=pointer]:
          - /url: /operations/control-tower
        - link "عملیات جدید" [ref=f2e51] [cursor=pointer]:
          - /url: /operations/shipments/new
        - region "اطلاعات سامانه" [ref=f2e53]:
          - paragraph [ref=f2e54]: Forwarder 1.10.0
      - navigation "بخش‌های پرونده حمل" [ref=f2e55]:
        - generic [ref=f2e56]:
          - link "خلاصه" [ref=f2e57] [cursor=pointer]:
            - /url: /operations/shipments/24219878-822f-4989-bc87-fc81d2f116e2/summary
          - link "مسیر و اجرا" [active] [ref=f2e58] [cursor=pointer]:
            - /url: /operations/shipments/24219878-822f-4989-bc87-fc81d2f116e2/route
          - link "کالا و تخصیص" [ref=f2e59] [cursor=pointer]:
            - /url: /operations/shipments/24219878-822f-4989-bc87-fc81d2f116e2/cargo
          - link "اسناد" [ref=f2e60] [cursor=pointer]:
            - /url: /operations/shipments/24219878-822f-4989-bc87-fc81d2f116e2/documents
          - link "پیگیری و ETA" [ref=f2e61] [cursor=pointer]:
            - /url: /operations/shipments/24219878-822f-4989-bc87-fc81d2f116e2/tracking
          - link "تحویل" [ref=f2e62] [cursor=pointer]:
            - /url: /operations/shipments/24219878-822f-4989-bc87-fc81d2f116e2/delivery
          - link "تکمیل و بستن" [ref=f2e63] [cursor=pointer]:
            - /url: /operations/shipments/24219878-822f-4989-bc87-fc81d2f116e2/closure
          - link "تاریخچه" [ref=f2e64] [cursor=pointer]:
            - /url: /operations/shipments/24219878-822f-4989-bc87-fc81d2f116e2/history
      - region [ref=f2e65]:
        - generic [ref=f2e66]:
          - paragraph [ref=f2e67]: اقدام جاری
          - heading "اصلاح و تکمیل سوابق" [level=2] [ref=f2e68]
          - paragraph [ref=f2e69]: اقدامات این بخش فقط بر پایه وضعیت و مجوزهای ثبت‌شده در سامانه نمایش داده می‌شوند.
      - region [ref=f2e70]:
        - generic [ref=f2e71]:
          - paragraph [ref=f2e72]: فضای کار محموله
          - heading "مسیر و اجرای عملیاتی" [level=2] [ref=f2e73]
        - generic [ref=f2e74]:
          - generic [ref=f2e75]:
            - heading "برنامه مسیر فعال" [level=3] [ref=f2e76]
            - paragraph [ref=f2e77]: "برنامه مسیر: بخش مشترک، شاخه‌های مقصد و وضعیت برنامه‌ریزی‌شده"
          - generic [ref=f2e78]:
            - article [ref=f2e79]:
              - generic [ref=f2e80]:
                - strong [ref=f2e81]: بخش مسیر 1 · جاده چین تا مرز
                - generic [ref=f2e82]: برنامه‌ریزی‌شده
              - paragraph [ref=f2e83]: بخش آغازین مشترک
              - paragraph [ref=f2e84]: تخت قیصر ← Seyyed Şobhān
              - paragraph [ref=f2e85]: جاده‌ای
              - paragraph [ref=f2e86]: "برنامه‌ریزی‌شده: ۱ اکتبر ۲۰۲۶ (۹ مهر ۱۴۰۵) · ۱۱:۲۶ (‎+۳:۳۰ گرینویچ) ← ۱ اکتبر ۲۰۲۶ (۹ مهر ۱۴۰۵) · ۱۹:۲۶ (‎+۳:۳۰ گرینویچ)"
              - paragraph [ref=f2e87]: "برآورد فعلی: ثبت نشده ← ثبت نشده"
              - paragraph [ref=f2e88]: "زمان واقعی رخدادهای قدیمی بخش: ثبت نشده ← ثبت نشده"
            - article [ref=f2e89]:
              - generic [ref=f2e90]:
                - strong [ref=f2e91]: بخش مسیر 2 · ریل خورگوس تا آکتائو
                - generic [ref=f2e92]: برنامه‌ریزی‌شده
              - paragraph [ref=f2e93]: شاخه از بخش 1
              - paragraph [ref=f2e94]: Seyyed Şobhān ← سید نور
              - paragraph [ref=f2e95]: ریلی
              - paragraph [ref=f2e96]: "برنامه‌ریزی‌شده: ۱ اکتبر ۲۰۲۶ (۹ مهر ۱۴۰۵) · ۲۱:۲۶ (‎+۳:۳۰ گرینویچ) ← ۳ اکتبر ۲۰۲۶ (۱۱ مهر ۱۴۰۵) · ۱۱:۲۶ (‎+۳:۳۰ گرینویچ)"
              - paragraph [ref=f2e97]: "برآورد فعلی: ثبت نشده ← ثبت نشده"
              - paragraph [ref=f2e98]: "زمان واقعی رخدادهای قدیمی بخش: ثبت نشده ← ثبت نشده"
            - article [ref=f2e99]:
              - generic [ref=f2e100]:
                - strong [ref=f2e101]: بخش مسیر 3
                - generic [ref=f2e102]: برنامه‌ریزی‌شده
              - paragraph [ref=f2e103]: شاخه از بخش 1
              - paragraph [ref=f2e104]: Seyyed Şobhān ← الوان
              - paragraph [ref=f2e105]: ریلی
              - paragraph [ref=f2e106]: "برنامه‌ریزی‌شده: ۱ اکتبر ۲۰۲۶ (۹ مهر ۱۴۰۵) · ۲۱:۲۶ (‎+۳:۳۰ گرینویچ) ← ۳ اکتبر ۲۰۲۶ (۱۱ مهر ۱۴۰۵) · ۱۱:۲۶ (‎+۳:۳۰ گرینویچ)"
              - paragraph [ref=f2e107]: "برآورد فعلی: ثبت نشده ← ثبت نشده"
              - paragraph [ref=f2e108]: "زمان واقعی رخدادهای قدیمی بخش: ثبت نشده ← ثبت نشده"
            - generic [ref=f2e109]:
              - heading "مقصد شاخه‌ای کالاها" [level=3] [ref=f2e110]
              - paragraph [ref=f2e111]: هر کالا به مقصد برنامه‌ریزی‌شده خودش متصل است؛ کالا و محموله تکثیر نشده‌اند.
              - paragraph [ref=f2e112]:
                - strong [ref=f2e113]: قطعات موتور
                - text: · ریل خورگوس تا آکتائو
              - paragraph [ref=f2e114]:
                - strong [ref=f2e115]: کالای مشتری دوم
                - text: · الوان
        - generic [ref=f2e116]:
          - generic [ref=f2e117]:
            - heading "وسیله و شرکت حمل هر بخش مسیر" [level=3] [ref=f2e118]
            - paragraph [ref=f2e119]: برای هر بخش مسیر می‌توان یک یا چند اجرای مستقل ثبت کرد. پس از آن، کالا را در بخش تخصیص همان مسیر ثبت کنید.
          - generic [ref=f2e120]:
            - region [ref=f2e121]:
              - heading "بخش مسیر 1 · جاده چین تا مرز" [level=3] [ref=f2e122]
              - paragraph [ref=f2e123]: تخت قیصر ← Seyyed Şobhān
              - generic [ref=f2e124]:
                - article [ref=f2e125]:
                  - generic [ref=f2e126]:
                    - heading "اجرای حمل" [level=4] [ref=f2e127]
                    - generic [ref=f2e128]: اطلاعات جاری
                  - generic [ref=f2e129]:
                    - paragraph [ref=f2e130]: شرکت حمل
                    - paragraph [ref=f2e131]: "[SHARED-E2E] Carrier X"
                    - paragraph [aria-hidden] [ref=f2e132]: ↓
                    - paragraph [ref=f2e133]: وسیله حمل
                    - paragraph [ref=f2e134]: کامیون آزمایشی · TRUCK-12
                    - generic [ref=f2e135]:
                      - paragraph [aria-hidden] [ref=f2e136]: ↓
                      - paragraph [ref=f2e137]: واحد / ظرف حمل 1
                      - paragraph [ref=f2e138]: تریلر آزمایشی · TRAILER-TRUCK-12
                  - group [ref=f2e139]:
                    - generic "تکمیل یا تغییر اطلاعات" [ref=f2e140] [cursor=pointer]
                    - option "انتخاب کنید"
                    - option "کامیون / کشنده جاده‌ای"
                    - option "قطار"
                    - option "کشتی"
                    - option "هواپیما"
                    - option "قطار آزمایشی"
                    - option "کامیون آزمایشی" [selected]
                    - option "فعلاً مشخص نیست"
                    - option "[SHARED-E2E] Carrier X" [selected]
                    - option "[SHARED-E2E] Carrier Y"
                    - option "[SHARED-E2E] Customer B"
                    - option "[SHARED-E2E] Customer C"
                    - option "نوع واحد / ظرف"
                    - option "تریلر چادری"
                    - option "تریلر کفی"
                    - option "تریلر مسقف / جعبه‌ای"
                    - option "تریلر یخچالی"
                    - option "تریلر تانکری"
                    - option "تریلر کمپرسی"
                    - option "کمرشکن / Low-bed"
                    - option "شاسی کانتینربر"
                    - option "واگن مسقف"
                    - option "واگن روباز"
                    - option "واگن کفی"
                    - option "واگن مخزن"
                    - option "واگن حمل کانتینر"
                    - option "کانتینر ۲۰ فوت استاندارد"
                    - option "کانتینر ۴۰ فوت استاندارد"
                    - option "کانتینر ۴۰ فوت High Cube"
                    - option "کانتینر ۲۰ فوت یخچالی"
                    - option "کانتینر ۴۰ فوت یخچالی"
                    - option "کانتینر Open Top"
                    - option "کانتینر Flat Rack"
                    - option "تانک کانتینر"
                    - option "پالت ULD هوایی"
                    - option "کانتینر ULD هوایی"
                    - option "کانتینر آزمایشی"
                    - option "تریلر آزمایشی" [selected]
                    - option "واگن آزمایشی"
                - article [ref=f2e141]:
                  - generic [ref=f2e142]:
                    - heading "اجرای حمل" [level=4] [ref=f2e143]
                    - generic [ref=f2e144]: اطلاعات جاری
                  - generic [ref=f2e145]:
                    - paragraph [ref=f2e146]: شرکت حمل
                    - paragraph [ref=f2e147]: "[SHARED-E2E] Carrier X"
                    - paragraph [aria-hidden] [ref=f2e148]: ↓
                    - paragraph [ref=f2e149]: وسیله حمل
                    - paragraph [ref=f2e150]: کامیون آزمایشی · TRUCK-18
                    - generic [ref=f2e151]:
                      - paragraph [aria-hidden] [ref=f2e152]: ↓
                      - paragraph [ref=f2e153]: واحد / ظرف حمل 1
                      - paragraph [ref=f2e154]: تریلر آزمایشی · TRAILER-TRUCK-18
                  - group [ref=f2e155]:
                    - generic "تکمیل یا تغییر اطلاعات" [ref=f2e156] [cursor=pointer]
                    - option "انتخاب کنید"
                    - option "کامیون / کشنده جاده‌ای"
                    - option "قطار"
                    - option "کشتی"
                    - option "هواپیما"
                    - option "قطار آزمایشی"
                    - option "کامیون آزمایشی" [selected]
                    - option "فعلاً مشخص نیست"
                    - option "[SHARED-E2E] Carrier X" [selected]
                    - option "[SHARED-E2E] Carrier Y"
                    - option "[SHARED-E2E] Customer B"
                    - option "[SHARED-E2E] Customer C"
                    - option "نوع واحد / ظرف"
                    - option "تریلر چادری"
                    - option "تریلر کفی"
                    - option "تریلر مسقف / جعبه‌ای"
                    - option "تریلر یخچالی"
                    - option "تریلر تانکری"
                    - option "تریلر کمپرسی"
                    - option "کمرشکن / Low-bed"
                    - option "شاسی کانتینربر"
                    - option "واگن مسقف"
                    - option "واگن روباز"
                    - option "واگن کفی"
                    - option "واگن مخزن"
                    - option "واگن حمل کانتینر"
                    - option "کانتینر ۲۰ فوت استاندارد"
                    - option "کانتینر ۴۰ فوت استاندارد"
                    - option "کانتینر ۴۰ فوت High Cube"
                    - option "کانتینر ۲۰ فوت یخچالی"
                    - option "کانتینر ۴۰ فوت یخچالی"
                    - option "کانتینر Open Top"
                    - option "کانتینر Flat Rack"
                    - option "تانک کانتینر"
                    - option "پالت ULD هوایی"
                    - option "کانتینر ULD هوایی"
                    - option "کانتینر آزمایشی"
                    - option "تریلر آزمایشی" [selected]
                    - option "واگن آزمایشی"
            - region [ref=f2e157]:
              - heading "بخش مسیر 2 · ریل خورگوس تا آکتائو" [level=3] [ref=f2e158]
              - paragraph [ref=f2e159]: Seyyed Şobhān ← سید نور
              - article [ref=f2e161]:
                - generic [ref=f2e162]:
                  - heading "اجرای حمل" [level=4] [ref=f2e163]
                  - generic [ref=f2e164]: اطلاعات جاری
                - generic [ref=f2e165]:
                  - paragraph [ref=f2e166]: شرکت حمل
                  - paragraph [ref=f2e167]: "[SHARED-E2E] Carrier X"
                  - paragraph [aria-hidden] [ref=f2e168]: ↓
                  - paragraph [ref=f2e169]: وسیله حمل
                  - paragraph [ref=f2e170]: قطار آزمایشی · WAGON-7
                  - generic [ref=f2e171]:
                    - paragraph [aria-hidden] [ref=f2e172]: ↓
                    - paragraph [ref=f2e173]: واحد / ظرف حمل 1
                    - paragraph [ref=f2e174]: واگن آزمایشی · WAGON-7
                - group [ref=f2e175]:
                  - generic "تکمیل یا تغییر اطلاعات" [ref=f2e176] [cursor=pointer]
                  - option "انتخاب کنید"
                  - option "کامیون / کشنده جاده‌ای"
                  - option "قطار"
                  - option "کشتی"
                  - option "هواپیما"
                  - option "قطار آزمایشی" [selected]
                  - option "کامیون آزمایشی"
                  - option "فعلاً مشخص نیست"
                  - option "[SHARED-E2E] Carrier X" [selected]
                  - option "[SHARED-E2E] Carrier Y"
                  - option "[SHARED-E2E] Customer B"
                  - option "[SHARED-E2E] Customer C"
                  - option "نوع واحد / ظرف"
                  - option "تریلر چادری"
                  - option "تریلر کفی"
                  - option "تریلر مسقف / جعبه‌ای"
                  - option "تریلر یخچالی"
                  - option "تریلر تانکری"
                  - option "تریلر کمپرسی"
                  - option "کمرشکن / Low-bed"
                  - option "شاسی کانتینربر"
                  - option "واگن مسقف"
                  - option "واگن روباز"
                  - option "واگن کفی"
                  - option "واگن مخزن"
                  - option "واگن حمل کانتینر"
                  - option "کانتینر ۲۰ فوت استاندارد"
                  - option "کانتینر ۴۰ فوت استاندارد"
                  - option "کانتینر ۴۰ فوت High Cube"
                  - option "کانتینر ۲۰ فوت یخچالی"
                  - option "کانتینر ۴۰ فوت یخچالی"
                  - option "کانتینر Open Top"
                  - option "کانتینر Flat Rack"
                  - option "تانک کانتینر"
                  - option "پالت ULD هوایی"
                  - option "کانتینر ULD هوایی"
                  - option "کانتینر آزمایشی"
                  - option "تریلر آزمایشی"
                  - option "واگن آزمایشی" [selected]
            - region [ref=f2e177]:
              - heading "بخش مسیر 3" [level=3] [ref=f2e178]
              - paragraph [ref=f2e179]: Seyyed Şobhān ← الوان
              - paragraph [ref=f2e180]: هنوز اجرای حملی برای این بخش ثبت نشده است.
        - group [ref=f2e181]:
          - generic "زمان مرجع و مبنای برنامه" [ref=f2e182] [cursor=pointer]
          - option "نسخه برنامه 1 · فعال" [selected]
        - generic [ref=f2e183]:
          - generic [ref=f2e184]:
            - heading "مسیر واقعی" [level=3] [ref=f2e185]
            - paragraph [ref=f2e186]: واقعیت پیمایش جدا از برنامه ثبت می‌شود. تفاوت مسیر به‌تنهایی مورد استثنا ایجاد نمی‌کند.
          - generic [ref=f2e187]:
            - paragraph [ref=f2e188]: هنوز واقعیت پیمایشی ثبت نشده است.
            - button "افزودن پیمایش واقعی" [ref=f2e189] [cursor=pointer]
      - group [ref=f2e190]:
        - generic "جزئیات اجرای مسیر" [ref=f2e191] [cursor=pointer]
        - generic [ref=f2e192]:
          - generic [ref=f2e194]:
            - heading "انحراف زمانی مسیر و استثناهای عملیاتی" [level=3] [ref=f2e196]
            - paragraph [ref=f2e198]: انحراف زمانی یا استثنای عملیاتی ثبت‌شده‌ای وجود ندارد.
          - generic [ref=f2e199]:
            - generic [ref=f2e200]:
              - heading "منبع" [level=3] [ref=f2e202]
              - generic [ref=f2e203]:
                - paragraph [ref=f2e204]: "منبع: عملیات مستقیم"
                - paragraph [ref=f2e205]: "درخواست: قابل اعمال نیست"
                - paragraph [ref=f2e206]: "پیشنهاد: قابل اعمال نیست"
            - region [ref=f2e207]:
              - generic [ref=f2e208]:
                - paragraph [ref=f2e209]: کنترل جاری
                - heading "مسائل عملیاتی" [level=2] [ref=f2e210]
                - paragraph [ref=f2e211]: انحراف زمانی، تأخیر، استثنا و موارد پیگیری در کنار هم دیده می‌شوند اما ماهیت مستقل خود را حفظ می‌کنند.
              - region "تأخیرها و استثناهای عملیاتی" [ref=f2e212]:
                - generic [ref=f2e213]:
                  - heading "تأخیرهای عملیاتی ثبت‌شده" [level=2] [ref=f2e214]
                  - paragraph [ref=f2e215]: موردی ثبت نشده است.
                - generic [ref=f2e216]:
                  - heading "استثناهای عملیاتی ثبت‌شده" [level=2] [ref=f2e217]
                  - paragraph [ref=f2e218]: موردی ثبت نشده است.
            - group [ref=f2e219]:
              - generic "جزئیات مالی محموله" [ref=f2e220] [cursor=pointer]
            - generic [ref=f2e221]:
              - heading "تطبیق خط زمانی" [level=3] [ref=f2e223]
              - generic [ref=f2e224]:
                - paragraph [ref=f2e225]: نسخه مسیر 1 · نسخه به‌روزرسانی برآورد 1 · آخرین به‌روزرسانی ثبت نشده
                - table [ref=f2e227]:
                  - rowgroup [ref=f2e228]:
                    - row [ref=f2e229]:
                      - columnheader "نقطه کنترل" [ref=f2e230]
                      - columnheader "برنامه‌ریزی‌شده" [ref=f2e231]
                      - columnheader "برآورد جاری" [ref=f2e232]
                      - columnheader "زمان واقعی" [ref=f2e233]
                      - columnheader "زمان مبنا / منبع" [ref=f2e234]
                      - columnheader "انحراف زمانی محاسبه‌شده" [ref=f2e235]
                  - rowgroup
                - paragraph [ref=f2e236]: ورودی خط زمانی وجود ندارد.
            - generic [ref=f2e237]:
              - heading "نقاط کنترل و چرخه عمر رویدادها" [level=3] [ref=f2e239]
              - paragraph [ref=f2e241]: نقطه کنترلی وجود ندارد.
            - generic [ref=f2e242]:
              - heading "بازبرنامه‌ریزی و نسخه‌های مسیر" [level=3] [ref=f2e244]
              - generic [ref=f2e246]:
                - strong [ref=f2e247]: نسخه مسیر 1
                - text: · نسخه فعال · نسخه رکورد 1
                - generic [ref=f2e248]: "واقعیت‌های پیمایش: 0 · انحراف‌های ثبت‌شده: 0"
            - generic [ref=f2e249]:
              - heading "استثناهای مسیر و موارد کاری" [level=3] [ref=f2e251]
              - generic [ref=f2e252]:
                - paragraph [ref=f2e253]: سابقه استثنای مسیر وجود ندارد.
                - heading "صف کار برج کنترل" [level=3] [ref=f2e254]
                - generic [ref=f2e255]:
                  - strong [ref=f2e256]: مورد نیازمند رسیدگی
                  - text: · باز · مهلت ۳۰ سپتامبر ۲۰۲۶ (۸ مهر ۱۴۰۵) · ۱۱:۲۷ (‎+۳:۳۰ گرینویچ) · نسخه 1
                - generic [ref=f2e257]:
                  - strong [ref=f2e258]: مورد نیازمند رسیدگی
                  - text: · باز · مهلت ۳۰ سپتامبر ۲۰۲۶ (۸ مهر ۱۴۰۵) · ۱۱:۲۷ (‎+۳:۳۰ گرینویچ) · نسخه 1
```

# Test source

```ts
  1   | import fs from "node:fs";
  2   | import path from "node:path";
  3   | import { expect, test, type Browser, type Page } from "@playwright/test";
  4   | import { openShipmentSection } from "./helpers/shipment-workspace";
  5   | 
  6   | const databaseUrl = process.env.E2E_DATABASE_URL;
  7   | const password = process.env.FORWARDER_E2E_PASSWORD;
  8   | const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
  9   | const evidencePath = process.env.PHASE3_FINAL_CANDIDATE_EVIDENCE_PATH;
  10  | if (!databaseUrl || !password || !fixturePath || !evidencePath) {
  11  |   throw new Error("FWD-IPJ-04 requires the owned final-candidate runtime inputs.");
  12  | }
  13  | if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_integrated_cert_p3_06_documents_p313_")) {
  14  |   throw new Error("FWD-IPJ-04 is restricted to its owned loopback database.");
  15  | }
  16  | 
  17  | const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  18  |   p313_shipment: string;
  19  |   p305_cargo: string;
  20  |   p308_cargo_b: string;
  21  |   p309_documents: Record<string, string>;
  22  |   p309_accounts: Record<string, { email: string }>;
  23  |   p313_target_label: string;
  24  |   p315_ipj04: {
  25  |     shipment: string;
  26  |     new_owner: string;
  27  |     original_report: string;
  28  |     corrected_report: string;
  29  |     eta_cargo: string;
  30  |     selected_route_time_versions: string[];
  31  |   };
  32  | };
  33  | 
  34  | test.setTimeout(300_000);
  35  | 
  36  | type BrowserEvidence = {
  37  |   consoleErrors: string[];
  38  |   pageErrors: string[];
  39  |   failedRequests: string[];
  40  |   unexpectedResponses: string[];
  41  | };
  42  | 
  43  | function observe(page: Page, expectedStatuses: number[] = []): BrowserEvidence {
  44  |   const evidence: BrowserEvidence = { consoleErrors: [], pageErrors: [], failedRequests: [], unexpectedResponses: [] };
  45  |   page.on("console", message => {
  46  |     const expected = expectedStatuses.some(status => message.text().includes(`status of ${status}`));
  47  |     if (message.type() === "error" && !expected) evidence.consoleErrors.push(message.text());
  48  |   });
  49  |   page.on("pageerror", error => evidence.pageErrors.push(error.message));
  50  |   page.on("requestfailed", request => evidence.failedRequests.push(`${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`));
  51  |   page.on("response", response => {
  52  |     if (response.url().includes("/api/") && response.status() >= 400 && !expectedStatuses.includes(response.status())) {
  53  |       evidence.unexpectedResponses.push(`${response.status()} ${response.request().method()} ${response.url()}`);
  54  |     }
  55  |   });
  56  |   return evidence;
  57  | }
  58  | 
  59  | function expectClean(evidence: BrowserEvidence) {
  60  |   expect(evidence.pageErrors, "uncaught browser errors").toEqual([]);
  61  |   const actionableFailures = evidence.failedRequests.filter(item =>
  62  |     !(item.includes("/closure") && item.endsWith("net::ERR_ABORTED")),
  63  |   );
> 64  |   expect(actionableFailures, "failed browser requests").toEqual([]);
      |                                                         ^ Error: failed browser requests
  65  |   expect(evidence.unexpectedResponses, "unexpected API responses").toEqual([]);
  66  |   expect(evidence.consoleErrors.filter(item => !item.includes("favicon")), "browser console errors").toEqual([]);
  67  | }
  68  | 
  69  | async function loginExpert(page: Page, persona: string, landing: RegExp) {
  70  |   await page.context().clearCookies();
  71  |   await page.goto("/");
  72  |   await page.evaluate(() => localStorage.clear());
  73  |   await page.reload();
  74  |   await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  75  |   await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);
  76  |   await page.getByLabel("رمز عبور").fill(password!);
  77  |   await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  78  |   await expect(page).toHaveURL(landing);
  79  | }
  80  | 
  81  | async function token(page: Page) {
  82  |   const value = await page.evaluate(() => localStorage.getItem("expert_token"));
  83  |   expect(value).toBeTruthy();
  84  |   return value!;
  85  | }
  86  | 
  87  | async function openCompletedShipment(page: Page) {
  88  |   await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).first().click();
  89  |   const all = page.getByRole("button", { name: "نمایش همه وضعیت‌ها", exact: true });
  90  |   if (await all.isVisible()) await all.click();
  91  |   await page.locator(`a[href="/operations/shipments/${fixture.p313_shipment}"]`).click();
  92  |   await expect(page.getByRole("heading", { name: "خلاصه محموله", exact: true })).toBeVisible();
  93  | }
  94  | 
  95  | async function loginCustomer(browser: Browser, name: "a" | "b") {
  96  |   const context = await browser.newContext({ locale: "fa-IR" });
  97  |   const page = await context.newPage();
  98  |   await page.goto("/customer");
  99  |   await page.locator("#customer-email").fill(fixture.p309_accounts[name].email);
  100 |   await page.locator("#customer-password").fill(password!);
  101 |   await page.locator("form button").first().click();
  102 |   await expect(page).toHaveURL(/\/customer\/requests$/);
  103 |   await page.getByRole("link", { name: "حمل‌های من", exact: true }).click();
  104 |   await page.locator(`a[href="/customer/shipments/${fixture.p313_shipment}"]`).click();
  105 |   await expect(page.getByRole("heading", { name: "کالاهای من", exact: true })).toBeVisible();
  106 |   return { context, page };
  107 | }
  108 | 
  109 | test("FWD-IPJ-04 continues one shared Shipment through history, ETA, privacy, closure, and post-close denial", async ({ browser }, testInfo) => {
  110 |   const ownerContext = await browser.newContext({ locale: "fa-IR" });
  111 |   const adminContext = await browser.newContext({ locale: "fa-IR" });
  112 |   const oldContext = await browser.newContext({ locale: "fa-IR" });
  113 |   const owner = await ownerContext.newPage();
  114 |   const admin = await adminContext.newPage();
  115 |   const old = await oldContext.newPage();
  116 |   const ownerEvidence = observe(owner, [409]);
  117 |   const adminEvidence = observe(admin);
  118 |   const oldEvidence = observe(old, [404]);
  119 | 
  120 |   await loginExpert(owner, "transfer_target", /\/operations$/);
  121 |   await openCompletedShipment(owner);
  122 |   await expect(owner.getByText(fixture.p313_target_label, { exact: true }).first()).toBeVisible();
  123 |   await expect(owner.getByText("قطعات موتور", { exact: true }).first()).toBeVisible();
  124 |   await expect(owner.getByText("کالای مشتری دوم", { exact: true }).first()).toBeVisible();
  125 | 
  126 |   await openShipmentSection(owner, "route", fixture.p313_shipment);
  127 |   await expect(owner.getByRole("heading", { name: "وسیله و شرکت حمل هر بخش مسیر" })).toBeVisible();
  128 |   await openShipmentSection(owner, "cargo", fixture.p313_shipment);
  129 |   await expect(owner.getByRole("heading", { name: "تخصیص و مسیر هر کالا" })).toBeVisible();
  130 | 
  131 |   const etaResponse = owner.waitForResponse(response =>
  132 |     response.url().includes(`/cargo/${fixture.p315_ipj04.eta_cargo}/eta/ensure`) && response.status() === 200,
  133 |   );
  134 |   await openShipmentSection(owner, "tracking", fixture.p313_shipment);
  135 |   await expect(owner.getByText("اصلاح‌شده؛ محفوظ در سابقه", { exact: true })).toBeVisible();
  136 |   await expect(owner.getByText("اصلاح موقعیت برای گواه پیوستگی سفر", { exact: false })).toBeVisible();
  137 |   const eta = await (await etaResponse).json() as { next: { available: boolean }; final: { available: boolean }; source_fingerprint?: string };
  138 |   expect(eta.next.available || eta.final.available).toBe(true);
  139 |   await expect(owner.getByRole("region", { name: "زمان تقریبی رسیدن کالا", exact: true }).first()).toContainText("زمان محاسبه:");
  140 | 
  141 |   await openShipmentSection(owner, "delivery", fixture.p313_shipment);
  142 |   await expect(owner.getByRole("region", { name: "تحویل کالاها" })).toContainText("نسخه اصلاحی جاری");
  143 |   await expect(owner.getByRole("region", { name: "تحویل کالاها" })).toContainText("سابقه تحویل‌های اصلاح‌شده");
  144 | 
  145 |   await openShipmentSection(owner, "history", fixture.p313_shipment);
  146 |   await expect(owner.getByRole("heading", { name: "تاریخچه یکپارچه محموله" })).toBeVisible();
  147 |   await expect(owner.getByLabel("تاریخچه عملیات حمل")).not.toContainText("دریافت تاریخچه عملیات ممکن نشد");
  148 | 
  149 |   const a = await loginCustomer(browser, "a");
  150 |   const b = await loginCustomer(browser, "b");
  151 |   await expect(a.page.getByText("قطعات موتور", { exact: true }).first()).toBeVisible();
  152 |   await expect(a.page.getByText("کالای مشتری دوم", { exact: true })).toHaveCount(0);
  153 |   await expect(a.page.locator("body")).not.toContainText("PRIVATE");
  154 |   await expect(b.page.getByText("کالای مشتری دوم", { exact: true }).first()).toBeVisible();
  155 |   await expect(b.page.getByText("قطعات موتور", { exact: true })).toHaveCount(0);
  156 |   await expect(b.page.locator("body")).not.toContainText("کالای شما از نقطه میانی عبور کرده است");
  157 |   await expect(b.page.locator("body")).not.toContainText("اصلاح موقعیت برای گواه پیوستگی سفر");
  158 |   expect((await a.page.request.get(`/api/customer/documents/${fixture.p309_documents.b}/download`)).status()).toBe(404);
  159 |   expect((await b.page.request.get(`/api/customer/documents/${fixture.p309_documents.a}/download`)).status()).toBe(404);
  160 | 
  161 |   await loginExpert(admin, "admin", /\/admin$/);
  162 |   await admin.getByRole("tab", { name: "قواعد بستن پرونده", exact: true }).click();
  163 |   await expect(admin.getByRole("heading", { name: "قواعد بستن پرونده" })).toBeVisible();
  164 |   await admin.getByRole("button", { name: "تعریف نسخه تازه قواعد" }).click();
```