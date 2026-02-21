"""Referral-based assignment engine: rules with conditions and distribution strategies."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.models import (
    ShipmentRequest,
    ExpertUser,
    ReferralRule,
    ReferralRuleState,
    ReferralAssignmentLog,
    CustomerGamification,
    CustomerWorkflowStep,
)
from backend.extensions import db

# Active statuses counted for workload (least_workload and max_active_assignments_per_expert)
ACTIVE_STATUSES = ("assigned", "in_progress", "quoted", "waiting_for_customer")

logger = logging.getLogger(__name__)


def _get_request_transport_method(request: ShipmentRequest) -> Optional[str]:
    """Return normalized transport method: road, rail, air, sea, or unknown."""
    raw = (
        request.domestic_transport_method
        or request.international_transport_method
        or request.transport_method
    )
    if not raw:
        return "unknown"
    s = (raw or "").strip().lower()
    if s in ("road", "rail", "air", "sea"):
        return s
    return "unknown"


def _conditions_match(request: ShipmentRequest, conditions: Dict[str, Any]) -> bool:
    """Return True if request matches rule conditions."""
    if conditions.get("shipping_type") is not None:
        if (request.shipping_type or "").strip().lower() != str(conditions["shipping_type"]).strip().lower():
            return False
    if conditions.get("transport_method") is not None:
        req_tm = _get_request_transport_method(request)
        rule_tm = (conditions.get("transport_method") or "").strip().lower()
        if rule_tm not in ("road", "rail", "air", "sea", "unknown"):
            rule_tm = "unknown"
        if req_tm != rule_tm:
            return False
    if conditions.get("origin_province") is not None:
        if request.origin_province_id != conditions.get("origin_province"):
            return False
    if conditions.get("destination_province") is not None:
        if request.dest_province_id != conditions.get("destination_province"):
            return False
    return True


def _referral_workload(session: Session, expert_id: int) -> int:
    """Count requests in active statuses for this expert (for referral engine only)."""
    return session.query(ShipmentRequest).filter(
        and_(
            ShipmentRequest.assigned_to == expert_id,
            ShipmentRequest.status.in_(ACTIVE_STATUSES),
        )
    ).count()


def _get_experts_by_ids(
    session: Session, expert_ids: List[int], only_assignable: bool = True
) -> List[ExpertUser]:
    """Return ExpertUser list for given ids, optionally filtered by active and role."""
    if not expert_ids:
        return []
    q = session.query(ExpertUser).filter(ExpertUser.id.in_(expert_ids))
    if only_assignable:
        q = q.filter(
            and_(
                ExpertUser.is_active == True,
                ExpertUser.role.in_(["expert", "business_expert"]),
            )
        )
    experts = q.all()
    # Preserve order of expert_ids
    by_id = {e.id: e for e in experts}
    return [by_id[eid] for eid in expert_ids if eid in by_id]


def _select_from_pool(
    session: Session,
    rule: ReferralRule,
    expert_ids: List[int],
    strategy: str,
    max_per_expert: Optional[int],
    request_id: int,
    dry_run: bool,
) -> Tuple[Optional[int], str, List[int], Dict[str, Any]]:
    """
    Select one expert from pool. Returns (expert_id, strategy_used, candidate_ids, debug).
    If dry_run, does not update ReferralRuleState.
    """
    debug: Dict[str, Any] = {"strategy": strategy, "expert_ids": expert_ids}
    candidates = _get_experts_by_ids(session, expert_ids)
    candidate_ids = [e.id for e in candidates]
    debug["candidates_after_active_filter"] = candidate_ids

    if max_per_expert is not None:
        within_cap = [
            eid for eid in candidate_ids
            if _referral_workload(session, eid) < max_per_expert
        ]
        debug["excluded_over_cap"] = [eid for eid in candidate_ids if eid not in within_cap]
        debug["max_active_assignments_per_expert"] = max_per_expert
        candidate_ids = within_cap

    if not candidate_ids:
        return None, strategy, candidate_ids, debug

    if strategy == "least_workload":
        workloads = [(eid, _referral_workload(session, eid)) for eid in candidate_ids]
        debug["workloads"] = {str(eid): w for eid, w in workloads}
        min_w = min(w for _, w in workloads)
        tied = [eid for eid, w in workloads if w == min_w]
        # Tie-breaker: prefer expert with smallest id (deterministic)
        selected = min(tied)
        debug["tie_breaker"] = "min_id"
        return selected, "least_workload", candidate_ids, debug

    if strategy == "round_robin":
        q = session.query(ReferralRuleState).filter(ReferralRuleState.rule_id == rule.id)
        if not dry_run:
            q = q.with_for_update()
        state = q.first()
        if not state:
            state = ReferralRuleState(rule_id=rule.id, rr_index=0, updated_at=datetime.now(timezone.utc))
            session.add(state)
            session.flush()
        n = len(candidate_ids)
        idx = state.rr_index % n
        selected = candidate_ids[idx]
        debug["rr_index_before"] = state.rr_index
        debug["rr_index_after"] = state.rr_index + 1
        debug["selected_index_in_pool"] = idx
        if not dry_run:
            state.rr_index = state.rr_index + 1
            state.updated_at = datetime.now(timezone.utc)
        return selected, "round_robin", candidate_ids, debug

    # Fallback: first candidate
    debug["fallback"] = "first_candidate"
    return candidate_ids[0], strategy or "pool", candidate_ids, debug


class ReferralEngine:
    """Engine for rule-based referral assignment with direct or pool strategies."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or db.session

    def auto_assign_request(self, request_id: int) -> Optional[int]:
        """
        Assign a shipment request using referral rules. One request -> one expert.
        Returns expert_id if assigned, None otherwise. Commits on success.
        """
        try:
            request = self.db.get(ShipmentRequest, request_id)
            if not request:
                logger.error(f"Shipment request {request_id} not found")
                return None
            if request.assigned_to:
                logger.info(f"Request {request_id} already assigned to {request.assigned_to}")
                return request.assigned_to

            rules = (
                self.db.query(ReferralRule)
                .filter(ReferralRule.is_active == True)
                .order_by(ReferralRule.priority.asc())
                .all()
            )
            for rule in rules:
                try:
                    conditions = json.loads(rule.conditions) if rule.conditions else {}
                except Exception:
                    conditions = {}
                if not _conditions_match(request, conditions):
                    continue
                try:
                    action = json.loads(rule.action) if rule.action else {}
                except Exception:
                    action = {}
                action_type = action.get("type")
                expert_id = None
                strategy_used = "direct"
                candidate_ids: List[int] = []
                debug: Dict[str, Any] = {}

                if action_type == "direct_assign":
                    eid = action.get("expert_id")
                    if eid is not None:
                        experts = _get_experts_by_ids(self.db, [eid])
                        if experts:
                            expert_id = experts[0].id
                            strategy_used = "direct"
                            candidate_ids = [expert_id]
                            debug = {"direct_assign": True}

                elif action_type == "pool_assign":
                    expert_ids = action.get("expert_ids") or []
                    strategy = action.get("strategy") or "round_robin"
                    max_per = action.get("max_active_assignments_per_expert")
                    expert_id, strategy_used, candidate_ids, debug = _select_from_pool(
                        self.db, rule, expert_ids, strategy, max_per, request.id, dry_run=False
                    )

                if expert_id:
                    self._assign_and_log(
                        request=request,
                        rule=rule,
                        expert_id=expert_id,
                        strategy_used=strategy_used,
                        candidate_expert_ids=candidate_ids,
                        debug=debug,
                    )
                    if getattr(rule, "stop_on_match", True):
                        return expert_id
                # else: no expert from this rule, try next rule
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in referral auto_assign_request {request_id}: {e}")
            raise

    def preview_assignment(self, request_id: int) -> Dict[str, Any]:
        """
        Compute which rule would match and which expert would be selected, without changing DB.
        Returns matched_rule, candidates, selected_expert, strategy_used, debug_trace.
        """
        result: Dict[str, Any] = {
            "matched_rule": None,
            "candidates": [],
            "selected_expert": None,
            "strategy_used": None,
            "debug_trace": {},
        }
        try:
            request = self.db.get(ShipmentRequest, request_id)
            if not request:
                result["error"] = "request_not_found"
                return result
            rules = (
                self.db.query(ReferralRule)
                .filter(ReferralRule.is_active == True)
                .order_by(ReferralRule.priority.asc())
                .all()
            )
            for rule in rules:
                try:
                    conditions = json.loads(rule.conditions) if rule.conditions else {}
                except Exception:
                    conditions = {}
                if not _conditions_match(request, conditions):
                    continue
                try:
                    action = json.loads(rule.action) if rule.action else {}
                except Exception:
                    action = {}
                action_type = action.get("type")
                expert_id = None
                strategy_used = None
                candidate_ids: List[int] = []
                debug: Dict[str, Any] = {}

                if action_type == "direct_assign":
                    eid = action.get("expert_id")
                    if eid is not None:
                        experts = _get_experts_by_ids(self.db, [eid])
                        if experts:
                            expert_id = experts[0].id
                            strategy_used = "direct"
                            candidate_ids = [expert_id]
                            debug = {"direct_assign": True}

                elif action_type == "pool_assign":
                    expert_ids = action.get("expert_ids") or []
                    strategy = action.get("strategy") or "round_robin"
                    max_per = action.get("max_active_assignments_per_expert")
                    expert_id, strategy_used, candidate_ids, debug = _select_from_pool(
                        self.db, rule, expert_ids, strategy, max_per, request.id, dry_run=True
                    )

                result["matched_rule"] = {
                    "id": rule.id,
                    "name": rule.name,
                    "priority": rule.priority,
                }
                result["candidates"] = candidate_ids
                result["debug_trace"] = debug
                result["strategy_used"] = strategy_used
                if expert_id:
                    expert = self.db.get(ExpertUser, expert_id)
                    result["selected_expert"] = (
                        {"id": expert.id, "full_name": expert.full_name} if expert else None
                    )
                else:
                    result["selected_expert"] = None
                return result
            return result
        except Exception as e:
            logger.exception("Preview assignment failed")
            result["error"] = str(e)
            return result

    def _assign_and_log(
        self,
        request: ShipmentRequest,
        rule: ReferralRule,
        expert_id: int,
        strategy_used: str,
        candidate_expert_ids: List[int],
        debug: Dict[str, Any],
    ) -> None:
        """Update request, create ReferralAssignmentLog, notification, and gamification. Commits."""
        expert = self.db.get(ExpertUser, expert_id)
        if not expert or not expert.is_active:
            raise ValueError(f"Expert {expert_id} is not active or does not exist")
        request.assigned_to = expert_id
        request.status = "assigned"
        request.has_unread_for_assignee = True
        log = ReferralAssignmentLog(
            request_id=request.id,
            rule_id=rule.id,
            selected_expert_id=expert_id,
            strategy_used=strategy_used,
            candidate_expert_ids=json.dumps(candidate_expert_ids),
            debug=json.dumps(debug, ensure_ascii=False),
            assigned_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
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
        logger.info(f"Referral: request {request.id} assigned to expert {expert_id} via rule {rule.id} ({strategy_used})")

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
