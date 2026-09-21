BEGIN TRANSACTION READ ONLY;

WITH facts AS (
    SELECT
        s.id,
        s.organization_id,
        s.source_type,
        s.shipment_request_id,
        s.accepted_quote_id,
        s.primary_responsible_expert_id,
        q.id AS quote_id,
        q.shipment_request_id AS quote_request_id,
        q.operational_organization_id AS quote_organization_id,
        q.created_by_expert_id AS quote_issuer_id,
        q.customer_response AS quote_response,
        qi.authority AS quote_issuer_authority,
        oi.authority AS persisted_owner_authority,
        (
            SELECT count(*)
            FROM operational_membership m
            WHERE m.user_id = q.created_by_expert_id
              AND m.organization_id = s.organization_id
        ) AS quote_issuer_membership_count,
        (
            SELECT count(*)
            FROM operational_membership m
            WHERE m.user_id = s.primary_responsible_expert_id
              AND m.organization_id = s.organization_id
        ) AS persisted_owner_membership_count
    FROM operational_shipment s
    LEFT JOIN expert_quote q ON q.id = s.accepted_quote_id
    LEFT JOIN expert_user qi ON qi.id = q.created_by_expert_id
    LEFT JOIN expert_user oi ON oi.id = s.primary_responsible_expert_id
), classified AS (
    SELECT id,
        CASE
            WHEN source_type = 'accepted_quote' THEN
                CASE
                    WHEN accepted_quote_id IS NULL OR shipment_request_id IS NULL
                        THEN 'MISSING_ACCEPTED_QUOTE_LINEAGE'
                    WHEN quote_id IS NULL
                        THEN 'MISSING_ACCEPTED_QUOTE'
                    WHEN quote_request_id IS DISTINCT FROM shipment_request_id
                      OR quote_organization_id IS DISTINCT FROM organization_id
                      OR quote_response IS DISTINCT FROM 'accepted'
                        THEN 'CONFLICTING_ACCEPTED_QUOTE_LINEAGE'
                    WHEN quote_issuer_id IS NULL
                      OR upper(coalesce(quote_issuer_authority, '')) <> 'EXPERT'
                      OR quote_issuer_membership_count <> 1
                        THEN 'INVALID_ACCEPTED_QUOTE_ISSUER'
                    WHEN primary_responsible_expert_id IS NULL
                        THEN 'DETERMINISTIC_REPAIR'
                    WHEN primary_responsible_expert_id <> quote_issuer_id
                        THEN 'PERSISTED_OWNER_CONFLICT'
                    ELSE 'ALREADY_VALID'
                END
            WHEN source_type = 'direct' THEN
                CASE
                    WHEN primary_responsible_expert_id IS NULL
                        THEN 'DIRECT_OWNER_MISSING'
                    WHEN upper(coalesce(persisted_owner_authority, '')) <> 'EXPERT'
                      OR persisted_owner_membership_count <> 1
                        THEN 'DIRECT_OWNER_INVALID'
                    ELSE 'ALREADY_VALID'
                END
            ELSE 'UNKNOWN_SOURCE_TYPE'
        END AS reason
    FROM facts
)
SELECT
    count(*) FILTER (WHERE reason = 'ALREADY_VALID')
        AS fixed_owner_already_valid_count,
    count(*) FILTER (WHERE reason = 'DETERMINISTIC_REPAIR')
        AS fixed_owner_deterministic_repair_count,
    count(*) FILTER (WHERE reason = 'CONFLICTING_ACCEPTED_QUOTE_LINEAGE')
        AS fixed_owner_ambiguous_count,
    count(*) FILTER (WHERE reason = 'PERSISTED_OWNER_CONFLICT')
        AS fixed_owner_contradiction_count,
    count(*) FILTER (WHERE reason NOT IN (
        'ALREADY_VALID',
        'DETERMINISTIC_REPAIR',
        'CONFLICTING_ACCEPTED_QUOTE_LINEAGE',
        'PERSISTED_OWNER_CONFLICT'
    )) AS fixed_owner_other_unresolved_count
FROM classified;

COMMIT;
