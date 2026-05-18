"""Read helpers for public tracking timeline construction."""
from sqlalchemy import func

from backend.extensions import db
from backend.models import AssignmentLog, ExpertConsoleLog, ReferralAssignmentLog

# Fixed 7 workflow steps (no email_verified). Order and completion derived from status.
WORKFLOW_STEP_DEFS = [
    {"name": "request_submitted", "order": 1, "title": "ارسال درخواست"},
    {"name": "expert_assigned", "order": 2, "title": "اختصاص کارشناس"},
    {"name": "expert_contacted", "order": 3, "title": "تماس کارشناس"},
    {"name": "quote_provided", "order": 4, "title": "ارائه پیشنهاد"},
    {"name": "contract_signed", "order": 5, "title": "امضای قرارداد"},
    {"name": "shipment_picked_up", "order": 6, "title": "تحویل مرسوله"},
    {"name": "shipment_delivered", "order": 7, "title": "تحویل به مقصد"},
]

# Status -> max completed step index (0-based). Steps 1..N are completed.
STATUS_TO_COMPLETED_UP_TO = {
    "new": 0,           # step 1 only
    "assigned": 1,      # 1,2
    "in_progress": 2,   # 1,2,3
    "quoted": 3,        # 1,2,3,4
    "waiting_for_customer": 3,  # 1,2,3,4
    "won": 6,           # all 7
    "lost": 1,          # 1,2
    "closed": 1,
    "cancelled": 1,
    "pending": 0,
}

# Fixed 4-step customer timeline. Step 4 title is dynamic (pending vs پذیرش/عدم پذیرش).
WORKFLOW_STEP_DEFS_SIMPLE_4 = [
    {"name": "request_submitted", "order": 1, "title": "ارسال درخواست"},
    {"name": "expert_assigned", "order": 2, "title": "اختصاص کارشناس"},
    {"name": "in_progress", "order": 3, "title": "در حال پیگیری"},
    {"name": "final_decision", "order": 4, "title": "پذیرش / عدم پذیرش"},  # base; overridden when completed
]


def build_workflow_steps_from_status(status: str, created_at, assigned_at=None, quote_created_at=None) -> list:
    """Build 7 workflow steps with is_completed and optional real completed_at."""
    max_completed = STATUS_TO_COMPLETED_UP_TO.get(status, 0)
    created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
    steps = []
    for i, defn in enumerate(WORKFLOW_STEP_DEFS):
        is_completed = i <= max_completed
        completed_at = None
        if is_completed:
            if i == 0:
                completed_at = created_iso
            elif i == 1 and assigned_at:
                completed_at = assigned_at.isoformat() if hasattr(assigned_at, "isoformat") else str(assigned_at)
            elif i == 3 and quote_created_at:
                completed_at = quote_created_at.isoformat() if hasattr(quote_created_at, "isoformat") else str(quote_created_at)
            else:
                completed_at = created_iso
        steps.append({
            "name": defn["name"],
            "order": defn["order"],
            "title": defn["title"],
            "is_completed": is_completed,
            "completed_at": completed_at,
            "points_earned": 0,
        })
    return steps


def get_final_decision_from_logs(shipment_request_id: int):
    """Return the most recent won/lost decision from ExpertConsoleLog, or None."""
    log = (
        db.session.query(ExpertConsoleLog)
        .filter(
            ExpertConsoleLog.shipment_request_id == shipment_request_id,
            ExpertConsoleLog.action == "status_change",
            ExpertConsoleLog.new_status.in_(["won", "lost"]),
        )
        .order_by(ExpertConsoleLog.created_at.desc())
        .first()
    )
    if not log or not log.new_status:
        return None
    completed_at = log.created_at.isoformat() if hasattr(log.created_at, "isoformat") else str(log.created_at)
    return {"decision": log.new_status, "completed_at": completed_at}


def get_assigned_at(req):
    """Return the earliest date when this request was assigned to an expert (from logs)."""
    dates = []
    first_al = (
        db.session.query(func.min(AssignmentLog.created_at))
        .filter(AssignmentLog.shipment_request_id == req.id)
        .scalar()
    )
    if first_al:
        dates.append(first_al)
    first_ral = (
        db.session.query(func.min(ReferralAssignmentLog.assigned_at))
        .filter(ReferralAssignmentLog.request_id == req.id)
        .scalar()
    )
    if first_ral:
        dates.append(first_ral)
    first_log = (
        db.session.query(func.min(ExpertConsoleLog.created_at))
        .filter(
            ExpertConsoleLog.shipment_request_id == req.id,
            ExpertConsoleLog.new_status == "assigned",
        )
        .scalar()
    )
    if first_log:
        dates.append(first_log)
    if not dates:
        return None
    return min(dates)


def build_workflow_steps_simple_4(req, assigned_at=None):
    """
    Build the 4-step customer timeline. Steps 1-3 are always completed (systematically).
    Step 4 is completed only when expert set won/lost; when status is closed without
    won/lost in history, step 4 stays pending with meta.warning.
    """
    status = req.status or "new"
    created_at = req.created_at
    created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
    if assigned_at is None:
        assigned_at = get_assigned_at(req)
    assigned_at_iso = (
        assigned_at.isoformat() if assigned_at and hasattr(assigned_at, "isoformat") else (str(assigned_at) if assigned_at else None)
    )
    step2_at = assigned_at_iso if assigned_at_iso else created_iso

    steps = []
    # Step 1: request_submitted — always completed at created_at
    steps.append({
        "name": WORKFLOW_STEP_DEFS_SIMPLE_4[0]["name"],
        "order": WORKFLOW_STEP_DEFS_SIMPLE_4[0]["order"],
        "title": WORKFLOW_STEP_DEFS_SIMPLE_4[0]["title"],
        "is_completed": True,
        "completed_at": created_iso,
    })
    # Step 2: expert_assigned — always completed at assigned_at or created_at
    steps.append({
        "name": WORKFLOW_STEP_DEFS_SIMPLE_4[1]["name"],
        "order": WORKFLOW_STEP_DEFS_SIMPLE_4[1]["order"],
        "title": WORKFLOW_STEP_DEFS_SIMPLE_4[1]["title"],
        "is_completed": True,
        "completed_at": step2_at,
    })
    # Step 3: in_progress — always completed at created_at (simplified UX)
    steps.append({
        "name": WORKFLOW_STEP_DEFS_SIMPLE_4[2]["name"],
        "order": WORKFLOW_STEP_DEFS_SIMPLE_4[2]["order"],
        "title": WORKFLOW_STEP_DEFS_SIMPLE_4[2]["title"],
        "is_completed": True,
        "completed_at": created_iso,
    })
    # Step 4: final_decision — from expert status or logs when closed
    step4_title = "پذیرش / عدم پذیرش"
    step4_completed = False
    step4_completed_at = None
    step4_meta = None

    if status == "won":
        step4_title = "پذیرش مشتری"
        decision = get_final_decision_from_logs(req.id)
        step4_completed_at = decision["completed_at"] if decision else created_iso
        step4_completed = True
    elif status == "lost":
        step4_title = "عدم پذیرش مشتری"
        decision = get_final_decision_from_logs(req.id)
        step4_completed_at = decision["completed_at"] if decision else created_iso
        step4_completed = True
    elif status == "closed":
        decision = get_final_decision_from_logs(req.id)
        if decision:
            step4_completed = True
            step4_completed_at = decision["completed_at"]
            step4_title = "پذیرش مشتری" if decision["decision"] == "won" else "عدم پذیرش مشتری"
        else:
            step4_meta = {"warning": "closed_without_decision"}

    step4 = {
        "name": WORKFLOW_STEP_DEFS_SIMPLE_4[3]["name"],
        "order": WORKFLOW_STEP_DEFS_SIMPLE_4[3]["order"],
        "title": step4_title,
        "is_completed": step4_completed,
        "completed_at": step4_completed_at,
    }
    if step4_meta:
        step4["meta"] = step4_meta
    steps.append(step4)
    return steps
