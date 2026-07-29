"""Auto-assignment engine for referral rules with round-robin fallback."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from backend.models import (
    ShipmentRequest,
    ExpertUser,
    ReferralRule,
    ReferralRuleState,
    ReferralAssignmentLog,
    ReferralAutoAssignState,
    ExpertConsoleLog,
    CustomerGamification,
    CustomerWorkflowStep,
)
from backend.extensions import db
from backend.services.expert_scope_service import can_handle_request, eligible_experts

logger = logging.getLogger(__name__)


def _get_assignable_experts(
    session: Session, request: ShipmentRequest | None = None
) -> List[ExpertUser]:
    """Return active experts (expert, business_expert) ordered by id for deterministic tie-break."""
    experts = (
        session.query(ExpertUser)
        .filter(
            and_(
                ExpertUser.is_active == True,
                ExpertUser.role.in_(["expert", "business_expert"]),
            )
        )
        .order_by(ExpertUser.id.asc())
        .all()
    )
    return eligible_experts(experts, request) if request is not None else experts


def _select_expert_by_last_assignment(
    session: Session, request: ShipmentRequest
) -> Optional[ExpertUser]:
    """
    Select the expert with the oldest last-assignment time (time-based round-robin).
    Experts with no assignment history are preferred (treated as oldest). Tie-break by ExpertUser.id.
    """
    experts = _get_assignable_experts(session, request)
    if not experts:
        return None
    # Subquery: last assigned_at per expert from ReferralAssignmentLog
    last_assigned_subq = (
        session.query(
            ReferralAssignmentLog.selected_expert_id.label("expert_id"),
            func.max(ReferralAssignmentLog.assigned_at).label("last_at"),
        )
        .group_by(ReferralAssignmentLog.selected_expert_id)
        .subquery()
    )
    # Join experts with last_assigned; order by last_at ASC NULLS FIRST, then id ASC
    expert_with_last = (
        session.query(ExpertUser)
        .outerjoin(last_assigned_subq, ExpertUser.id == last_assigned_subq.c.expert_id)
        .filter(
            and_(
                ExpertUser.is_active == True,
                ExpertUser.role.in_(["expert", "business_expert"]),
            )
        )
        .order_by(last_assigned_subq.c.last_at.asc().nulls_first(), ExpertUser.id.asc())
    )
    return next(
        (expert for expert in expert_with_last.all() if can_handle_request(expert, request)),
        None,
    )


def _json_object(value: str | None) -> Dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _request_transport_values(request: ShipmentRequest) -> set[str]:
    return {
        value.strip().lower()
        for value in (
            request.transport_method,
            request.domestic_transport_method,
            request.international_transport_method,
        )
        if isinstance(value, str) and value.strip()
    }


def _condition_matches(actual: Any, expected: Any) -> bool:
    if expected in (None, "", []):
        return True
    if isinstance(expected, list):
        return str(actual) in {str(item) for item in expected}
    return str(actual) == str(expected)


def _rule_matches_request(rule: ReferralRule, request: ShipmentRequest) -> bool:
    conditions = _json_object(rule.conditions)
    if not _condition_matches(request.shipping_type, conditions.get("shipping_type")):
        return False

    transport_method = conditions.get("transport_method")
    if transport_method not in (None, "", []):
        transport_values = _request_transport_values(request)
        expected_values = transport_method if isinstance(transport_method, list) else [transport_method]
        if not transport_values.intersection({str(value).strip().lower() for value in expected_values}):
            return False

    if not _condition_matches(request.origin_province_id, conditions.get("origin_province")):
        return False
    if not _condition_matches(request.dest_province_id, conditions.get("destination_province")):
        return False

    return True


def _active_assignment_count(session: Session, expert_id: int) -> int:
    return (
        session.query(func.count(ShipmentRequest.id))
        .filter(
            and_(
                ShipmentRequest.assigned_to == expert_id,
                ShipmentRequest.status.in_(["assigned", "in_progress", "quoted", "waiting_for_customer"]),
            )
        )
        .scalar()
        or 0
    )


def _assignable_pool(
    session: Session,
    expert_ids: list[int],
    request: ShipmentRequest,
    max_active: Any = None,
) -> list[ExpertUser]:
    if not expert_ids:
        return []

    experts = (
        session.query(ExpertUser)
        .filter(
            and_(
                ExpertUser.id.in_(expert_ids),
                ExpertUser.is_active == True,
                ExpertUser.role.in_(["expert", "business_expert"]),
            )
        )
        .all()
    )
    by_id = {expert.id: expert for expert in experts}
    ordered = eligible_experts(
        [by_id[expert_id] for expert_id in expert_ids if expert_id in by_id],
        request,
    )

    if max_active in (None, ""):
        return ordered

    try:
        max_active_count = int(max_active)
    except (TypeError, ValueError):
        return ordered

    return [
        expert
        for expert in ordered
        if _active_assignment_count(session, expert.id) < max_active_count
    ]


def _parse_expert_ids(value: Any) -> list[int]:
    expert_ids = []
    for item in value or []:
        try:
            expert_ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return expert_ids


class ReferralEngine:
    """Auto-assigns new requests using active referral rules, then global round-robin fallback."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or db.session

    def auto_assign_request(self, request_id: int) -> Optional[int]:
        """
        Assign a shipment request to the expert with oldest last-assignment time.
        Returns expert_id if assigned, None if no experts. Commits on success.
        Uses row lock on ReferralAutoAssignState(id=1) for concurrency safety.
        """
        try:
            request = self.db.get(ShipmentRequest, request_id)
            if not request:
                logger.error(f"Shipment request {request_id} not found")
                return None
            if request.assigned_to:
                logger.info(f"Request {request_id} already assigned to {request.assigned_to}")
                return request.assigned_to

            experts = _get_assignable_experts(self.db, request)
            if not experts:
                logger.warning("No active experts for auto-assignment")
                return None

            rule_assignment = self._select_matching_rule_assignment(request)
            if rule_assignment:
                self._advance_rule_state(rule_assignment)
                self._assign_and_log(
                    request=request,
                    expert_id=rule_assignment["expert_id"],
                    candidate_expert_ids=rule_assignment["candidate_expert_ids"],
                    debug=rule_assignment["debug"],
                    rule_id=rule_assignment["rule_id"],
                    strategy_used=rule_assignment["strategy_used"],
                )
                return rule_assignment["expert_id"]

            # Ensure lock row exists, then take row lock for concurrency
            state = self.db.query(ReferralAutoAssignState).filter(ReferralAutoAssignState.id == 1).first()
            if not state:
                state = ReferralAutoAssignState(id=1, last_index=0, updated_at=datetime.now(timezone.utc))
                self.db.add(state)
                self.db.flush()
            state = (
                self.db.query(ReferralAutoAssignState)
                .filter(ReferralAutoAssignState.id == 1)
                .with_for_update()
                .first()
            )

            selected = _select_expert_by_last_assignment(self.db, request)
            if not selected:
                return None
            expert_id = selected.id
            expert_ids = [e.id for e in experts]

            self._assign_and_log(
                request=request,
                expert_id=expert_id,
                candidate_expert_ids=expert_ids,
                debug={
                    "round_robin": "time_based",
                    "total_experts": len(expert_ids),
                },
            )
            return expert_id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in referral auto_assign_request {request_id}: {e}")
            raise

    def preview_assignment(self, request_id: int) -> Dict[str, Any]:
        """
        Preview which expert would get the next assignment (time-based round-robin), without changing DB.
        """
        result: Dict[str, Any] = {
            "matched_rule": None,
            "candidates": [],
            "selected_expert": None,
            "strategy_used": "round_robin",
            "debug_trace": {},
        }
        try:
            request = self.db.get(ShipmentRequest, request_id)
            if not request:
                result["error"] = "request_not_found"
                return result
            experts = _get_assignable_experts(self.db, request)
            if not experts:
                result["error"] = "no_experts"
                return result
            rule_assignment = self._select_matching_rule_assignment(request, dry_run=True)
            if rule_assignment:
                expert = self.db.get(ExpertUser, rule_assignment["expert_id"])
                result["matched_rule"] = rule_assignment["matched_rule"]
                result["candidates"] = rule_assignment["candidate_expert_ids"]
                result["selected_expert"] = {"id": expert.id, "full_name": expert.full_name} if expert else None
                result["strategy_used"] = rule_assignment["strategy_used"]
                result["debug_trace"] = rule_assignment["debug"]
                return result
            expert_ids = [e.id for e in experts]
            selected = _select_expert_by_last_assignment(self.db, request)
            if not selected:
                result["error"] = "no_experts"
                return result
            expert_id = selected.id
            expert = self.db.get(ExpertUser, expert_id)
            result["candidates"] = expert_ids
            result["selected_expert"] = {"id": expert.id, "full_name": expert.full_name} if expert else None
            result["debug_trace"] = {"round_robin": "time_based", "total_experts": len(expert_ids)}
            return result
        except Exception as e:
            logger.exception("Preview assignment failed")
            result["error"] = str(e)
            return result

    def _select_matching_rule_assignment(self, request: ShipmentRequest, dry_run: bool = False) -> Optional[Dict[str, Any]]:
        rules = (
            self.db.query(ReferralRule)
            .filter(ReferralRule.is_active == True)
            .order_by(ReferralRule.priority.asc(), ReferralRule.name.asc())
            .all()
        )

        for rule in rules:
            if not _rule_matches_request(rule, request):
                continue

            action = _json_object(rule.action)
            action_type = action.get("type")
            if action_type == "direct_assign":
                expert = self.db.get(ExpertUser, action.get("expert_id"))
                if not expert or not can_handle_request(expert, request):
                    if getattr(rule, "stop_on_match", True):
                        return None
                    continue
                return {
                    "rule_id": rule.id,
                    "matched_rule": {"id": rule.id, "name": rule.name, "priority": rule.priority},
                    "expert_id": expert.id,
                    "candidate_expert_ids": [expert.id],
                    "strategy_used": "direct",
                    "debug": {
                        "matched_rule": rule.name,
                        "action_type": action_type,
                        "conditions": _json_object(rule.conditions),
                        "dry_run": dry_run,
                    },
                }

            if action_type == "pool_assign":
                candidate_ids = _parse_expert_ids(action.get("expert_ids", []))
                candidates = _assignable_pool(
                    self.db,
                    candidate_ids,
                    request,
                    action.get("max_active_assignments_per_expert"),
                )
                if not candidates:
                    if getattr(rule, "stop_on_match", True):
                        return None
                    continue

                strategy = action.get("strategy") or "round_robin"
                selected_index = 0
                if strategy == "least_workload":
                    selected = min(candidates, key=lambda expert: (_active_assignment_count(self.db, expert.id), expert.id))
                else:
                    state = self.db.query(ReferralRuleState).filter(ReferralRuleState.rule_id == rule.id).first()
                    rr_index = state.rr_index if state else 0
                    selected_index = rr_index % len(candidates)
                    selected = candidates[selected_index]
                    strategy = "round_robin"

                return {
                    "rule_id": rule.id,
                    "matched_rule": {"id": rule.id, "name": rule.name, "priority": rule.priority},
                    "expert_id": selected.id,
                    "candidate_expert_ids": [expert.id for expert in candidates],
                    "strategy_used": strategy,
                    "selected_index": selected_index,
                    "debug": {
                        "matched_rule": rule.name,
                        "action_type": action_type,
                        "conditions": _json_object(rule.conditions),
                        "dry_run": dry_run,
                    },
                }

        return None

    def _advance_rule_state(self, assignment: Dict[str, Any]) -> None:
        if assignment.get("strategy_used") != "round_robin" or not assignment.get("rule_id"):
            return
        state = self.db.query(ReferralRuleState).filter(ReferralRuleState.rule_id == assignment["rule_id"]).first()
        if not state:
            state = ReferralRuleState(rule_id=assignment["rule_id"], rr_index=0)
            self.db.add(state)
            self.db.flush()
        candidate_count = max(len(assignment.get("candidate_expert_ids") or []), 1)
        state.rr_index = (int(assignment.get("selected_index", 0)) + 1) % candidate_count
        state.updated_at = datetime.now(timezone.utc)

    def _assign_and_log(
        self,
        request: ShipmentRequest,
        expert_id: int,
        candidate_expert_ids: List[int],
        debug: Dict[str, Any],
        rule_id: Optional[int] = None,
        strategy_used: str = "round_robin",
    ) -> None:
        """Update request, create ReferralAssignmentLog, ExpertConsoleLog, notification, gamification. Commits."""
        expert = self.db.get(ExpertUser, expert_id)
        if not expert or not can_handle_request(expert, request):
            raise ValueError(f"Expert {expert_id} is not active or does not exist")
        request.assigned_to = expert_id
        request.status = "assigned"
        request.has_unread_for_assignee = True
        from backend.services.sla_service import set_initial_assignment_sla
        set_initial_assignment_sla(request, expert)
        log = ReferralAssignmentLog(
            request_id=request.id,
            rule_id=rule_id,
            selected_expert_id=expert_id,
            strategy_used=strategy_used,
            candidate_expert_ids=json.dumps(candidate_expert_ids),
            debug=json.dumps(debug, ensure_ascii=False),
            assigned_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        # ExpertConsoleLog for timeline consistency (same as manual assignment)
        console_log = ExpertConsoleLog(
            shipment_request_id=request.id,
            expert_user_id=expert_id,
            action="assignment",
            old_status="new",
            new_status="assigned",
            note=f"ارجاع خودکار ({strategy_used})",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(console_log)
        self._create_assignment_notification(expert_id, request.id)
        if getattr(request, "gamification_customer_id", None):
            try:
                workflow_step = CustomerWorkflowStep(
                    customer_id=request.gamification_customer_id,
                    shipment_request_id=request.id,
                    step_name="expert_assigned",
                    step_order=3,
                    is_completed=True,
                    completed_at=datetime.now(timezone.utc),
                    points_earned=15,
                )
                self.db.add(workflow_step)
                customer = self.db.query(CustomerGamification).filter(
                    CustomerGamification.id == request.gamification_customer_id
                ).first()
                if customer:
                    customer.update_loyalty_points(15)
            except Exception as e:
                logger.error(f"Gamification on referral assign: {e}")
        self.db.commit()
        logger.info(f"Auto-assign: request {request.id} -> expert {expert_id} ({strategy_used})")

    def _create_assignment_notification(self, expert_id: int, request_id: int) -> None:
        from backend.models import ExpertConsoleNotification
        n = ExpertConsoleNotification(
            expert_user_id=expert_id,
            shipment_request_id=request_id,
            notification_type="request_assigned",
            title="درخواست جدید ارجاع داده شد",
            message="یک درخواست حمل و نقل جدید به شما ارجاع داده شد.",
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(n)


referral_engine = ReferralEngine()
