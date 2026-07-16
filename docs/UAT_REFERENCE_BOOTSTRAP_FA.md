# Bootstrap مرجع Candidate UAT

ابزار `scripts/bootstrap_uat_candidate.py` منبع `forwarder_db` در revision `54ea21ea0d9f` را فقط داخل تراکنش read-only می‌خواند و فقط target با پیشوند `forwarder_candidate_uat_` را می‌پذیرد.

ترتیب: migration عادی تا head، ایجاد ایران با `IR`، انتقال معنایی 31 Province، 425 County و 425 City بدون حفظ IDهای منبع، انتقال 12 Port و بازتولید 372 coverage موروثی UAT. هیچ user، hash، Customer، ShipmentRequest یا جدول legacy منتقل نمی‌شود.

Port Seed و Customs هیچ geography ایجاد نمی‌کنند. Customs dataset وجود ندارد و حدس زده نمی‌شود؛ بنابراین شمارش Customs و Port-Customs صفر و وضعیت `CUSTOMS_REFERENCE_DATA_PENDING` است. این Candidate فقط برای UAT است و Production cutover را مجاز نمی‌کند.
