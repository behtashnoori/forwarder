BEGIN TRANSACTION READ ONLY;

WITH owner_facts AS (
    SELECT s.id,s.organization_id,s.source_type,s.shipment_request_id,
           s.accepted_quote_id,s.primary_responsible_expert_id,
           q.shipment_request_id AS quote_request_id,
           q.operational_organization_id AS quote_organization_id,
           q.created_by_expert_id AS quote_issuer_id,
           q.customer_response AS quote_response,
           qi.authority AS quote_issuer_authority,
           oi.authority AS owner_authority,
           (SELECT count(*) FROM operational_membership m
             WHERE m.user_id=q.created_by_expert_id
               AND m.organization_id=s.organization_id) AS quote_memberships,
           (SELECT count(*) FROM operational_membership m
             WHERE m.user_id=s.primary_responsible_expert_id
               AND m.organization_id=s.organization_id) AS owner_memberships
    FROM operational_shipment s
    LEFT JOIN expert_quote q ON q.id=s.accepted_quote_id
    LEFT JOIN expert_user qi ON qi.id=q.created_by_expert_id
    LEFT JOIN expert_user oi ON oi.id=s.primary_responsible_expert_id
), checks(check_code,check_state,safe_detail) AS (
    SELECT 'DATABASE_HEAD_EXACT',
           CASE WHEN (SELECT count(*) FROM alembic_version)=1
                  AND (SELECT min(version_num) FROM alembic_version)='20260926_fixed_shipment_responsible_expert'
                THEN 'PASS' ELSE 'BLOCKED' END,
           'one_20260926_fixed_shipment_responsible_expert'
    UNION ALL
    SELECT 'FIXED_OWNER_NOT_NULL',
           CASE WHEN NOT EXISTS (SELECT 1 FROM operational_shipment WHERE primary_responsible_expert_id IS NULL)
                THEN 'PASS' ELSE 'BLOCKED' END,
           'no_null_primary_responsible_expert_id'
    UNION ALL
    SELECT 'ACCEPTED_QUOTE_OWNER_LINEAGE',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM owner_facts
                    WHERE source_type='accepted_quote' AND (
                        accepted_quote_id IS NULL OR shipment_request_id IS NULL
                        OR quote_request_id IS DISTINCT FROM shipment_request_id
                        OR quote_organization_id IS DISTINCT FROM organization_id
                        OR quote_response IS DISTINCT FROM 'accepted'
                        OR quote_issuer_id IS NULL
                        OR upper(coalesce(quote_issuer_authority,''))<>'EXPERT'
                        OR quote_memberships<>1
                        OR primary_responsible_expert_id IS DISTINCT FROM quote_issuer_id
                    )
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'exact_accepted_quote_issuer_owner'
    UNION ALL
    SELECT 'DIRECT_OWNER_VALIDITY',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM owner_facts
                    WHERE source_type='direct' AND (
                        primary_responsible_expert_id IS NULL
                        OR upper(coalesce(owner_authority,''))<>'EXPERT'
                        OR owner_memberships<>1
                    )
                ) AND NOT EXISTS (
                    SELECT 1 FROM owner_facts WHERE source_type NOT IN ('accepted_quote','direct')
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'direct_owner_historical_predicate'
    UNION ALL
    SELECT 'FIXED_OWNER_FUNCTION_PRESENT',
           CASE WHEN EXISTS (SELECT 1 FROM pg_proc WHERE proname='prevent_operational_shipment_owner_change')
                THEN 'PASS' ELSE 'BLOCKED' END,
           'prevent_operational_shipment_owner_change'
    UNION ALL
    SELECT 'FIXED_OWNER_TRIGGER_ENABLED',
           CASE WHEN EXISTS (
                    SELECT 1 FROM pg_trigger
                    WHERE tgname='trg_operational_shipment_fixed_owner'
                      AND NOT tgisinternal AND tgenabled<>'D'
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'trg_operational_shipment_fixed_owner'
    UNION ALL
    SELECT 'QUOTE_PUBLIC_ID_COMPLETE_UNIQUE',
           CASE WHEN NOT EXISTS (SELECT 1 FROM expert_quote WHERE public_id IS NULL)
                  AND NOT EXISTS (SELECT 1 FROM expert_quote GROUP BY public_id HAVING count(*)>1)
                THEN 'PASS' ELSE 'BLOCKED' END,
           'public_id_nonnull_unique'
    UNION ALL
    SELECT 'QUOTE_RESPONSE_CONSTRAINTS_PRESENT',
           CASE WHEN (
                    SELECT count(*) FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
                    WHERE t.relname='expert_quote'
                      AND c.conname IN ('ck_expert_quote_customer_response','ck_expert_quote_response_message')
                      AND c.contype='c'
                )=2 THEN 'PASS' ELSE 'BLOCKED' END,
           'response_and_message_constraints'
    UNION ALL
    SELECT 'REQUEST_CARGO_SCHEMA_PRESENT',
           CASE WHEN to_regclass('public.request_cargo_item') IS NOT NULL
                  AND (SELECT count(*) FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
                       WHERE t.relname='request_cargo_item'
                         AND c.conname IN ('uq_request_cargo_item_public_id','uq_request_cargo_item_request_position',
                           'ck_request_cargo_item_position_positive','ck_request_cargo_item_description_nonblank',
                           'ck_request_cargo_item_quantity_positive','ck_request_cargo_item_quantity_uom_pair',
                           'ck_request_cargo_item_meaningful'))=7
                THEN 'PASS' ELSE 'BLOCKED' END,
           'request_cargo_table_and_constraints'
    UNION ALL
    SELECT 'REQUEST_CARGO_NO_SYNTHETIC_ROWS',
           CASE WHEN (SELECT count(*) FROM request_cargo_item)=0 THEN 'PASS' ELSE 'BLOCKED' END,
           'expected_zero_immediately_after_migration'
    UNION ALL
    SELECT 'NOTIFICATION_SCHEMA_PRESENT',
           CASE WHEN to_regclass('public.notification_action') IS NOT NULL
                  AND to_regclass('public.notification_attempt') IS NOT NULL
                THEN 'PASS' ELSE 'BLOCKED' END,
           'notification_foundation_and_lifecycle'
    UNION ALL
    SELECT 'NOTIFICATION_NO_MIGRATION_ROWS',
           CASE WHEN (SELECT count(*) FROM notification_action)=0
                  AND (SELECT count(*) FROM notification_attempt)=0
                THEN 'PASS' ELSE 'BLOCKED' END,
           'expected_zero_immediately_after_migration'
)
SELECT check_code,check_state,safe_detail FROM checks ORDER BY check_code;

COMMIT;
