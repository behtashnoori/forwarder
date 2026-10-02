"""Permit one explicit route-time basis pin on an active, unstarted leg."""

from alembic import op


revision = "20261016_active_route_basis"
down_revision = "20261015_org_shipment_stages"
branch_labels = None
depends_on = None


ACTIVE_BASIS_GUARD = r"""
CREATE OR REPLACE FUNCTION public.check_route_time_basis() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
DECLARE
  leg record;
  reference record;
  latest integer;
BEGIN
  SELECT l.*, p.status AS plan_status, p.is_active AS plan_is_active,
         s.lifecycle_status AS shipment_status
    INTO leg
    FROM public.route_leg l
    JOIN public.route_plan p ON p.id = l.route_plan_id
    JOIN public.operational_shipment s ON s.id = p.operational_shipment_id
   WHERE l.id = NEW.route_leg_id
   FOR UPDATE OF l;
  SELECT r.*, v.effective_from, v.id AS version_id
    INTO reference
    FROM public.organization_route_time_version v
    JOIN public.organization_route_time r ON r.id = v.reference_id
   WHERE v.id = NEW.reference_version_id
   FOR UPDATE OF r;
  SELECT COALESCE(MAX(selection_revision), 0)
    INTO latest
    FROM public.route_leg_time_basis
   WHERE route_leg_id = NEW.route_leg_id;

  IF NEW.selection_revision <> latest + 1 THEN
    RAISE EXCEPTION 'Selection revision must be sequential';
  END IF;
  IF leg.shipment_status IN ('closed', 'cancelled') THEN
    RAISE EXCEPTION 'Closed or cancelled shipment cannot accept a route basis';
  END IF;
  IF leg.plan_status = 'active' THEN
    IF NOT leg.plan_is_active THEN
      RAISE EXCEPTION 'Inactive route plan cannot accept a route basis';
    END IF;
    IF latest <> 0 THEN
      RAISE EXCEPTION 'Active route basis is already pinned';
    END IF;
    IF leg.status NOT IN ('planned', 'ready')
       OR leg.actual_departure IS NOT NULL
       OR leg.actual_arrival IS NOT NULL THEN
      RAISE EXCEPTION 'Started route leg cannot accept a route basis';
    END IF;
  ELSIF leg.plan_status <> 'draft' THEN
    RAISE EXCEPTION 'Published route basis is immutable';
  END IF;
  IF reference.origin_location_id IS DISTINCT FROM leg.origin_location_id
     OR reference.destination_location_id IS DISTINCT FROM leg.destination_location_id
     OR reference.origin_point_id IS DISTINCT FROM leg.origin_logistics_point_id
     OR reference.destination_point_id IS DISTINCT FROM leg.destination_logistics_point_id
     OR reference.transport_mode IS DISTINCT FROM leg.transport_mode THEN
    RAISE EXCEPTION 'Reference does not match route leg';
  END IF;
  IF leg.planned_departure IS NOT NULL
     AND leg.planned_departure IS DISTINCT FROM NEW.reference_at THEN
    RAISE EXCEPTION 'Reference basis differs from planned departure';
  END IF;
  IF reference.effective_from > NEW.reference_at
     OR EXISTS (
       SELECT 1
         FROM public.organization_route_time_version v
        WHERE v.reference_id = reference.id
          AND v.effective_from > reference.effective_from
          AND v.effective_from <= NEW.reference_at
     ) THEN
    RAISE EXCEPTION 'Reference version is not applicable';
  END IF;
  RETURN NEW;
END $$
"""


LEGACY_DRAFT_ONLY_GUARD = r"""
CREATE OR REPLACE FUNCTION public.check_route_time_basis() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE leg record; reference record; latest integer;
BEGIN
  SELECT l.*,p.status AS plan_status INTO leg FROM public.route_leg l JOIN public.route_plan p ON p.id=l.route_plan_id WHERE l.id=NEW.route_leg_id FOR UPDATE OF l;
  SELECT r.*,v.effective_from,v.id AS version_id INTO reference FROM public.organization_route_time_version v JOIN public.organization_route_time r ON r.id=v.reference_id WHERE v.id=NEW.reference_version_id FOR UPDATE OF r;
  SELECT COALESCE(MAX(selection_revision),0) INTO latest FROM public.route_leg_time_basis WHERE route_leg_id=NEW.route_leg_id;
  IF NEW.selection_revision <> latest+1 THEN RAISE EXCEPTION 'Selection revision must be sequential'; END IF;
  IF leg.plan_status <> 'draft' THEN RAISE EXCEPTION 'Published route basis is immutable'; END IF;
  IF reference.origin_location_id IS DISTINCT FROM leg.origin_location_id OR reference.destination_location_id IS DISTINCT FROM leg.destination_location_id OR reference.origin_point_id IS DISTINCT FROM leg.origin_logistics_point_id OR reference.destination_point_id IS DISTINCT FROM leg.destination_logistics_point_id OR reference.transport_mode IS DISTINCT FROM leg.transport_mode THEN RAISE EXCEPTION 'Reference does not match route leg'; END IF;
  IF leg.planned_departure IS NOT NULL AND leg.planned_departure IS DISTINCT FROM NEW.reference_at THEN RAISE EXCEPTION 'Reference basis differs from planned departure'; END IF;
  IF reference.effective_from > NEW.reference_at OR EXISTS (SELECT 1 FROM public.organization_route_time_version v WHERE v.reference_id=reference.id AND v.effective_from > reference.effective_from AND v.effective_from <= NEW.reference_at) THEN RAISE EXCEPTION 'Reference version is not applicable'; END IF;
  RETURN NEW;
END $$
"""


def upgrade():
    op.execute(ACTIVE_BASIS_GUARD)


def downgrade():
    op.execute(LEGACY_DRAFT_ONLY_GUARD)
