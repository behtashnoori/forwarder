# موتور ارجاع (Referral Engine)

## هدف

هر درخواست جدید فقط به **یک کارشناس** ارجاع می‌شود. وقتی در یک قانون چند کارشناس تعریف شده‌اند (Pool)، سیستم ارجاع‌ها را **بین آن‌ها توزیع** می‌کند (Round-robin یا کمترین بار کاری).

---

## ۱. نحوه کار موتور

- قوانین **فعال** به ترتیب **اولویت (priority)** از کم به زیاد اجرا می‌شوند (عدد کمتر = اولویت بالاتر).
- برای هر قانون، ابتدا **شرط‌ها (conditions)** روی درخواست بررسی می‌شوند. در صورت تطابق:
  - **direct_assign**: همان کارشناس مشخص‌شده انتخاب می‌شود (در صورت فعال و واجد نقش بودن).
  - **pool_assign**: از بین لیست کارشناسان با یکی از استراتژی‌های **round_robin** یا **least_workload** یک نفر انتخاب می‌شود؛ در صورت تعریف **max_active_assignments_per_expert**، کارشناسانی که به سقف رسیده‌اند از لیست نامزدها حذف می‌شوند.
- با انتخاب کارشناس، درخواست به او assign می‌شود، وضعیت به `assigned` تغییر می‌کند و یک رکورد **ReferralAssignmentLog** ثبت می‌شود.
- اگر **stop_on_match = true** باشد، پس از اولین ارجاع موفق خروج انجام می‌شود؛ وگرنه قانون بعدی هم بررسی می‌شود.
- اگر هیچ قانونی منطبق نبود یا برای هیچ قانونی کارشناس واجد شرایط نمانده باشد، درخواست **بدون ارجاع** می‌ماند و وضعیت آن **new** است.

### توزیع

| استراتژی | کاربرد |
|----------|--------|
| **round_robin** | توزیع نوبتی بین کارشناسان pool؛ با هر ارجاع، نوبت به نفر بعدی می‌رود (state در `ReferralRuleState.rr_index`). |
| **least_workload** | انتخاب کارشناس با کمترین تعداد درخواست فعال (وضعیت‌های assigned, in_progress, quoted, waiting_for_customer). در تساوی، کمترین id انتخاب می‌شود. |

---

## ۲. قرارداد داده (Data contracts)

### Conditions (شرط‌ها)

مقدار `null` یا عدم ارسال یعنی «هر مقداری».

```json
{
  "shipping_type": "domestic | international | null",
  "transport_method": "road | rail | air | sea | unknown | null",
  "origin_province": number | null,
  "destination_province": number | null
}
```

- **shipping_type**: نوع ارسال درخواست (`domestic` / `international`).
- **transport_method**: روش حمل نرمال‌شده (`road`, `rail`, `air`, `sea`, `unknown`).
- **origin_province** / **destination_province**: شناسه استان مبدا/مقصد (اختیاری).

### Action — ارجاع مستقیم

```json
{
  "type": "direct_assign",
  "expert_id": 123
}
```

### Action — ارجاع از Pool

```json
{
  "type": "pool_assign",
  "expert_ids": [10, 11, 12],
  "strategy": "round_robin | least_workload",
  "max_active_assignments_per_expert": 5
}
```

- **max_active_assignments_per_expert**: اختیاری؛ اگر تعریف شود، کارشناسانی که تعداد درخواست‌های فعالشان >= این مقدار است از نامزدها حذف می‌شوند.

---

## ۳. مثال‌های سه قانون واقعی

### قانون ۱: درخواست بین‌المللی → Pool A با Round-robin

- **نام**: ارجاع بین‌المللی به تیم A
- **شرط**: `shipping_type = "international"`.
- **اکشن**: `pool_assign` با `expert_ids = [1, 2, 3]` و `strategy = "round_robin"`.
- **اولویت**: 1.

درخواست‌های بین‌المللی به‌صورت نوبتی بین کارشناسان ۱، ۲ و ۳ توزیع می‌شوند.

### قانون ۲: ارجاع مستقیم به یک کارشناس

- **نام**: حمل هوایی به کارشناس ثابت
- **شرط**: `transport_method = "air"`.
- **اکشن**: `direct_assign` با `expert_id = 5`.
- **اولویت**: 2.

هر درخواست با روش حمل هوایی مستقیماً به کارشناس ۵ ارجاع می‌شود.

### قانون ۳: Pool با کمترین بار و سقف ظرفیت

- **نام**: داخلی جاده‌ای با تعادل بار
- **شرط**: `shipping_type = "domestic"`, `transport_method = "road"`.
- **اکشن**: `pool_assign` با `expert_ids = [10, 11]`, `strategy = "least_workload"`, `max_active_assignments_per_expert = 3`.
- **اولویت**: 3.

از بین کارشناسان ۱۰ و ۱۱، کسی که تعداد درخواست‌های فعالش کمتر است انتخاب می‌شود؛ و اگر هر دو به سقف ۳ رسیده باشند، این قانون کارشناس برنمی‌گرداند و در صورت عدم stop_on_match قانون بعدی امتحان می‌شود.

---

## ۴. سناریوهای تست

### ۴.۱ توزیع Round-robin (۱۰ درخواست پشت‌سرهم، ۳ کارشناس)

- یک قانون فعال با `pool_assign`, `expert_ids = [E1, E2, E3]`, `strategy = "round_robin"`.
- ارسال ۱۰ درخواست که همگی با این قانون match می‌کنند.
- **انتظار**: توزیع نوبتی؛ مثلاً E1, E2, E3, E1, E2, E3, E1, E2, E3, E1 (با توجه به مقدار اولیه `rr_index`).

### ۴.۲ کمترین بار کاری (یکی ۵، دیگری ۱)

- یک قانون با `pool_assign`, `expert_ids = [E1, E2]`, `strategy = "least_workload"`.
- E1 دارای ۵ درخواست فعال، E2 دارای ۱ درخواست فعال.
- **انتظار**: انتخاب E2 (کمترین workload).

### ۴.۳ ظرفیت پر شده و انتخاب کارشناس بعدی

- قانون با `pool_assign`, `expert_ids = [E1, E2, E3]`, `strategy = "round_robin"`, `max_active_assignments_per_expert = 2`.
- E1 و E2 هر کدام ۲ درخواست فعال دارند؛ E3 صفر.
- **انتظار**: E1 و E2 از نامزدها حذف می‌شوند؛ تنها E3 انتخاب می‌شود.

---

## ۵. یکپارچه‌سازی با ثبت درخواست

پس از ثبت موفق **ShipmentRequest**، تابع **`auto_assign_request(request_id)`** فراخوانی می‌شود:

- در صورت ارجاع: وضعیت درخواست = **assigned** و فیلد **assigned_to** تنظیم می‌شود.
- در صورت عدم ارجاع: وضعیت = **new** و درخواست بدون ارجاع می‌ماند.

---

## ۶. APIهای ادمین

- `GET /api/admin/referral-rules` — لیست قوانین
- `POST /api/admin/referral-rules` — ایجاد قانون
- `PUT /api/admin/referral-rules/{id}` — به‌روزرسانی
- `DELETE /api/admin/referral-rules/{id}` — حذف
- `POST /api/admin/referral-rules/preview` — پیش‌نمایش (ورودی: `request_id`؛ خروجی: قانون منطبق، نامزدها، کارشناس انتخاب‌شده، استراتژی، debug_trace؛ بدون تغییر در دیتابیس)
