BEGIN TRANSACTION READ ONLY;

WITH checks(check_code, check_state, safe_detail) AS (
    SELECT 'CURRENT_REVISION_EXACT',
           CASE WHEN (SELECT count(*) FROM alembic_version) = 1
                  AND (SELECT min(version_num) FROM alembic_version) = '20260921_shipment_evidence_ownership'
                THEN 'PASS' ELSE 'BLOCKED' END,
           'expected_one_20260921_shipment_evidence_ownership'
    UNION ALL
    SELECT 'SOURCE_TABLES_PRESENT',
           CASE WHEN to_regclass('public.operational_outbox') IS NOT NULL
                  AND to_regclass('public.operational_organization') IS NOT NULL
                  AND to_regclass('public.operational_shipment') IS NOT NULL
                  AND to_regclass('public.expert_quote') IS NOT NULL
                  AND to_regclass('public.expert_user') IS NOT NULL
                  AND to_regclass('public.operational_membership') IS NOT NULL
                  AND to_regclass('public.shipment_request') IS NOT NULL
                  AND to_regclass('public.cargo_type') IS NOT NULL
                  AND to_regclass('public.unit_of_measure') IS NOT NULL
                  AND to_regclass('public.customer_gamification') IS NOT NULL
                THEN 'PASS' ELSE 'BLOCKED' END,
           'pending_path_source_relations'
    UNION ALL
    SELECT 'OPERATIONAL_OUTBOX_TENANT_COLUMNS',
           CASE WHEN EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='operational_outbox'
                      AND column_name='id' AND data_type='bigint'
                ) AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='operational_outbox'
                      AND column_name='organization_id' AND data_type='bigint'
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'operational_outbox_id_organization_id_bigint'
    UNION ALL
    SELECT 'SHIPMENT_OWNER_SOURCE_COLUMNS',
           CASE WHEN (
                    SELECT count(*) FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='operational_shipment'
                      AND column_name IN ('id','organization_id','source_type','shipment_request_id','accepted_quote_id','primary_responsible_expert_id')
                ) = 6 THEN 'PASS' ELSE 'BLOCKED' END,
           'operational_shipment_adr047_columns'
    UNION ALL
    SELECT 'SHIPMENT_OWNER_CURRENTLY_NULLABLE',
           CASE WHEN EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='operational_shipment'
                      AND column_name='primary_responsible_expert_id'
                      AND data_type='bigint' AND is_nullable='YES'
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'primary_responsible_expert_id_bigint_nullable'
    UNION ALL
    SELECT 'QUOTE_SOURCE_COLUMNS',
           CASE WHEN (
                    SELECT count(*) FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='expert_quote'
                      AND column_name IN ('id','shipment_request_id','operational_organization_id','created_by_expert_id','customer_response')
                ) = 5 THEN 'PASS' ELSE 'BLOCKED' END,
           'expert_quote_pending_path_columns'
    UNION ALL
    SELECT 'QUOTE_HISTORICAL_RESPONSE_VALUES',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM expert_quote
                    WHERE customer_response IS NOT NULL
                      AND customer_response NOT IN ('accepted','declined')
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'null_accepted_declined_only'
    UNION ALL
    SELECT 'QUOTE_REQUEST_RELATIONSHIP',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM expert_quote q
                    LEFT JOIN shipment_request r ON r.id=q.shipment_request_id
                    WHERE q.shipment_request_id IS NULL OR r.id IS NULL
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'no_missing_or_orphan_quote_request'
    UNION ALL
    SELECT 'QUOTE_ISSUER_RELATIONSHIP',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM expert_quote q
                    LEFT JOIN expert_user u ON u.id=q.created_by_expert_id
                    WHERE q.created_by_expert_id IS NULL OR u.id IS NULL
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'no_missing_or_orphan_quote_issuer'
    UNION ALL
    SELECT 'OUTBOX_TENANT_UNIQUENESS_PREREQUISITE',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM operational_outbox
                    GROUP BY id,organization_id HAVING count(*)>1
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'no_duplicate_id_organization_id_pairs'
    UNION ALL
    SELECT 'CARGO_PARENT_KEYS_PRESENT',
           CASE WHEN (
                    SELECT count(*) FROM information_schema.columns
                    WHERE table_schema='public'
                      AND ((table_name='shipment_request' AND column_name='id' AND data_type='bigint')
                        OR (table_name='cargo_type' AND column_name='id' AND data_type='bigint')
                        OR (table_name='unit_of_measure' AND column_name='id' AND data_type='bigint'))
                ) = 3 THEN 'PASS' ELSE 'BLOCKED' END,
           'request_cargo_parent_bigint_keys'
    UNION ALL
    SELECT 'TARGET_TABLES_ABSENT',
           CASE WHEN to_regclass('public.notification_action') IS NULL
                  AND to_regclass('public.notification_attempt') IS NULL
                  AND to_regclass('public.request_cargo_item') IS NULL
                THEN 'PASS' ELSE 'BLOCKED' END,
           'notification_action_notification_attempt_request_cargo_item'
    UNION ALL
    SELECT 'TARGET_QUOTE_COLUMNS_ABSENT',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='expert_quote'
                      AND column_name IN ('public_id','customer_response_message','responded_by_customer_id')
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'expert_quote_new_columns'
    UNION ALL
    SELECT 'TARGET_CONSTRAINT_NAMES_AVAILABLE',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname IN (
                        'uq_operational_outbox_tenant','uq_notification_action_public_id',
                        'uq_notification_action_tenant','uq_notification_action_idempotency',
                        'fk_notification_action_source_event_tenant','ck_notification_action_status',
                        'uq_notification_attempt_public_id','uq_notification_attempt_number',
                        'fk_notification_attempt_action_tenant','ck_notification_attempt_number_positive',
                        'ck_notification_attempt_status','uq_notification_attempt_claim_token',
                        'ck_notification_attempt_claim_pair','uq_request_cargo_item_public_id',
                        'uq_request_cargo_item_request_position','ck_request_cargo_item_position_positive',
                        'ck_request_cargo_item_description_nonblank','ck_request_cargo_item_quantity_positive',
                        'ck_request_cargo_item_quantity_uom_pair','ck_request_cargo_item_meaningful',
                        'fk_expert_quote_responded_by_customer','uq_expert_quote_public_id',
                        'ck_expert_quote_response_message'
                    )
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'pending_path_constraint_names'
    UNION ALL
    SELECT 'TARGET_INDEX_NAMES_AVAILABLE',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM pg_class
                    WHERE relkind='i' AND relname IN (
                        'ix_notification_action_org_status','ix_notification_action_correlation',
                        'ix_notification_attempt_org_status','ix_request_cargo_item_request',
                        'ix_expert_quote_responded_by_customer_id'
                    )
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'pending_path_index_names'
    UNION ALL
    SELECT 'FIXED_OWNER_GUARD_ABSENT',
           CASE WHEN NOT EXISTS (
                    SELECT 1 FROM pg_trigger
                    WHERE tgname='trg_operational_shipment_fixed_owner' AND NOT tgisinternal
                ) AND NOT EXISTS (
                    SELECT 1 FROM pg_proc WHERE proname='prevent_operational_shipment_owner_change'
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'pre_migration_trigger_function_absence'
    UNION ALL
    SELECT 'BASELINE_QUOTE_RESPONSE_CONSTRAINT_PRESENT',
           CASE WHEN EXISTS (
                    SELECT 1 FROM pg_constraint c
                    JOIN pg_class t ON t.oid=c.conrelid
                    WHERE t.relname='expert_quote'
                      AND c.conname='ck_expert_quote_customer_response'
                      AND c.contype='c'
                ) THEN 'PASS' ELSE 'BLOCKED' END,
           'current_quote_response_constraint'
)
SELECT check_code,check_state,safe_detail FROM checks ORDER BY check_code;

COMMIT;
