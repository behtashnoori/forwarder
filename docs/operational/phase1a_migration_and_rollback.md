# Phase 1A migration and rollback

Revision `20260729_operational_vertical_slice` follows `20260728_add_quote_customer_response`. Upgrade is additive and creates operational tables, indexes, constraints, and PostgreSQL append-only/scope triggers. Downgrade drops triggers/functions first, then Phase 1A tables and the nullable Quote organization link.

Validated on a disposable PostgreSQL 18 cluster: fresh head upgrade, single head/current check, head→previous→head, trigger removal/restoration, constraints, concurrent create, optimistic conflict, and cleanup. Production was untouched.
