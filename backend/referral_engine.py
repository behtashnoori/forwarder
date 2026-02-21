"""Auto-assignment engine: round-robin among all active experts. No rules to define."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.models import (
    ShipmentRequest,
    ExpertUser,
    ReferralAssignmentLog,
    ReferralAutoAssignState,
    CustomerGamification,
    CustomerWorkflowStep,
)
from backend.extensions import db

logger = logging.getLogger(__name__)


def _get_assignable_experts(session: Session) -> List[ExpertUser]:
    """Return active experts (expert, business_expert) ordered by id for deterministic round-robin."""
    return (
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


class ReferralEngine:
    """Auto-assigns each new request to the next expert in round-robin order. No rules."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or db.session

    def auto_assign_request(self, request_id: int) -> Optional[int]:
        """
        Assign a shipment request to the next expert in round-robin order.
        Returns expert_id if assigned, None if no experts. Commits on success.
        """
        try:
            request = self.db.get(ShipmentRequest, request_id)
            if not request:
                logger.error(f"Shipment request {request_id} not found")
                return None
            if request.assigned_to:
                logger.info(f"Request {request_id} already assigned to {request.assigned_to}")
                return request.assigned_to

            experts = _get_assignable_experts(self.db)
            if not experts:
                logger.warning("No active experts for auto-assignment")
                return None

            expert_ids = [e.id for e in experts]
            state = self.db.query(ReferralAutoAssignState).filter(ReferralAutoAssignState.id == 1).first()
            if not state:
                state = ReferralAutoAssignState(id=1, last_index=0, updated_at=datetime.now(timezone.utc))
                self.db.add(state)
                self.db.flush()

            idx = state.last_index % len(expert_ids)
            expert_id = expert_ids[idx]
            state.last_index = state.last_index + 1
            state.updated_at = datetime.now(timezone.utc)

            self._assign_and_log(
                request=request,
                expert_id=expert_id,
                candidate_expert_ids=expert_ids,
                debug={"round_robin_index": idx, "total_experts": len(expert_ids)},
            )
            return expert_id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in referral auto_assign_request {request_id}: {e}")
            raise

    def preview_assignment(self, request_id: int) -> Dict[str, Any]:
        """
        Preview which expert would get the next assignment (round-robin), without changing DB.
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
            experts = _get_assignable_experts(self.db)
            if not experts:
                result["error"] = "no_experts"
                return result
            expert_ids = [e.id for e in experts]
            state = self.db.query(ReferralAutoAssignState).filter(ReferralAutoAssignState.id == 1).first()
            idx = (state.last_index if state else 0) % len(expert_ids)
            expert_id = expert_ids[idx]
            expert = self.db.get(ExpertUser, expert_id)
            result["candidates"] = expert_ids
            result["selected_expert"] = {"id": expert.id, "full_name": expert.full_name} if expert else None
            result["debug_trace"] = {"round_robin_index": idx, "total_experts": len(expert_ids)}
            return result
        except Exception as e:
            logger.exception("Preview assignment failed")
            result["error"] = str(e)
            return result

    def _assign_and_log(
        self,
        request: ShipmentRequest,
        expert_id: int,
        candidate_expert_ids: List[int],
        debug: Dict[str, Any],
    ) -> None:
        """Update request, create log (rule_id=None), notification, gamification. Commits."""
        expert = self.db.get(ExpertUser, expert_id)
        if not expert or not expert.is_active:
            raise ValueError(f"Expert {expert_id} is not active or does not exist")
        request.assigned_to = expert_id
        request.status = "assigned"
        request.has_unread_for_assignee = True
        log = ReferralAssignmentLog(
            request_id=request.id,
            rule_id=None,
            selected_expert_id=expert_id,
            strategy_used="round_robin",
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
        logger.info(f"Auto-assign: request {request.id} -> expert {expert_id} (round_robin)")

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
