# Phase 0 Permission Matrix

مدل مجوز: `(principal, action, resource, organization_scope, attributes)`. UI guard مجوز نیست؛ backend policy enforcement و audit الزامی است.

## نقش‌ها

- Sales، Pricing، Operator، Dispatcher، ControlTower، ProjectManager، Finance، Compliance، Partner، Customer، Admin، Auditor.
- نقش و scope واقعی سازمان **نیازمند تأیید** است؛ جدول زیر baseline freeze است.

Legend: `M` مدیریت، `V` مشاهده، `S` مشاهده محدود به scope، `A` approval ویژه، `—` ممنوع.

| Resource / Action | Sales | Pricing | Operator | Dispatcher | Tower | PM | Finance | Compliance | Partner | Customer | Admin | Auditor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ShipmentRequest read | M | V | V | V | V | V | S | S | — | S | M | V |
| Quote write/approve | — | M/A | — | — | — | — | V | — | — | response only | A | V |
| Convert accepted quote | — | V | M | M | — | — | — | — | — | — | M | V |
| OperationalShipment read | V | V | M | M | M | M | S | S | S | S | M | V |
| Shipment lifecycle command | — | — | M | M | V | A | — | — | — | — | A | V |
| RoutePlan/RouteLeg write | — | — | M | M | V | A | — | S | S | — | M | V |
| Milestone plan write | — | — | M | M | V | A | — | M | S | — | M | V |
| MilestoneEvent submit | — | — | M | M | M | — | — | S | S | — | M | V |
| MilestoneEvent verify | — | — | M | M | M | A | — | A | — | — | A | V |
| Exception manage | V | — | M | M | M | A | S | S | S | — | M | V |
| WorkItem claim/resolve | — | — | M | M | M | M | S | S | S | — | M | V |
| Internal note | — | — | M | M | M | M | S | S | S | — | M | V |
| Public/customer projection | V | V | V | V | V | V | V | V | S | S | M | V |
| Cost actual/margin | — | V | S | S | S | V | M/A | — | S own | — | A | V |
| Document classified | — | — | S | S | S | S | S | M/A | S | S allowed | M | V |
| Policy/role config | — | — | — | — | — | — | — | — | — | — | M/A | V |
| Audit export | — | — | — | — | S | S | S | S | — | — | A | M |

## Permission boundaries قطعی

1. Sales/Pricing حق write وضعیت عملیاتی ندارند.
2. Operator حق تغییر نتیجه quote ندارد.
3. Customer/Partner فقط resourceهای organization/assignment خود را می‌بینند.
4. internal note، cost و raw evidence در projection عمومی ممنوع‌اند.
5. waive/cancel-after-start/correction نیازمند reason و elevated permission است.
6. Admin bypass خاموش نیست؛ action حساس Admin نیز audit و در صورت policy approval می‌خواهد.
7. Auditor read-only است.

## Segregation of Duties

| کنترل | قاعده |
|---|---|
| Quote approval | creator و approver برای threshold مصوب متفاوت؛ threshold نیازمند تأیید |
| Milestone override | submitter نمی‌تواند override حساس خود را verify کند |
| Cost approval | creator charge و approver طبق threshold جدا |
| Permission change | actor نمی‌تواند elevation خود را بدون approver انجام دهد |
| Audit | audit record توسط business API قابل حذف نیست |

## Policy inputs

`principal_id`, roles، organization ids، team ids، resource organization/owner، classification، shipment lifecycle، action، request time و service account identity.

## خطا و Audit

deny-by-default. پاسخ بیرونی `403 OPERATION_FORBIDDEN` بدون افشای resource است. audit شامل policy version، decision، actor/service، scope، correlation و reason می‌شود. retention و break-glass **نیازمند تأیید** است.
