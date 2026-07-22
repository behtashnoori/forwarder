# ADR-003: اصطلاح رسمی OperationalShipment

- Status: Accepted

## Decision

نام canonical پرونده اجرا `OperationalShipment` است. `ShipmentJob` فقط alias منسوخ در توضیحات migration/ارتباط انسانی است و هیچ entity، class، table، endpoint یا schema با این نام ایجاد نمی‌شود.

## Rationale

OperationalShipment مرز آن را با ShipmentRequest روشن و معنای end-to-end را بیان می‌کند. نگهداری دو نام برای یک مفهوم باعث duplicate model و API ambiguity می‌شود.

## Consequences

همه کد و مستندات آینده از نام canonical استفاده می‌کنند. lint/architecture review باید terminology drift را رد کند.
