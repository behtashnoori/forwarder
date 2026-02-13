"""Automatic assignment engine for shipment requests."""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session

from backend.models import (
    ShipmentRequest, ExpertUser, TransportMethod, ExpertSpecialization,
    AssignmentRule, AssignmentLog, CustomerGamification, CustomerWorkflowStep
)
from backend.extensions import db

logger = logging.getLogger(__name__)


class AssignmentEngine:
    """Engine for automatically assigning shipment requests to experts."""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or db.session
    
    def assign_request(self, request_id: int, assignment_method: str = "automatic", reason: str = None) -> Optional[int]:
        """
        Assign a shipment request to the most suitable expert.
        
        Args:
            request_id: ID of the shipment request
            assignment_method: "automatic", "manual", or "override"
            reason: Optional detailed reason for assignment
            
        Returns:
            ID of assigned expert or None if no suitable expert found
        """
        try:
            # Get the shipment request
            request = self.db.query(ShipmentRequest).get(request_id)
            if not request:
                logger.error(f"Shipment request {request_id} not found")
                return None
            
            # Skip if already assigned (unless override)
            if request.assigned_to and assignment_method != "override":
                logger.info(f"Request {request_id} already assigned to expert {request.assigned_to}")
                return request.assigned_to
            
            # Find the best expert
            expert_id = self._find_best_expert(request)
            
            if expert_id:
                # Assign the request
                self._assign_to_expert(request, expert_id, assignment_method, reason)
                logger.info(f"Request {request_id} assigned to expert {expert_id} via {assignment_method}")
                return expert_id
            else:
                logger.warning(f"No suitable expert found for request {request_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error assigning request {request_id}: {e}")
            return None
    
    def _find_best_expert(self, request: ShipmentRequest) -> Optional[int]:
        """Find the best expert for a shipment request."""
        try:
            # Get active assignment rules ordered by priority
            rules = self.db.query(AssignmentRule).filter(
                AssignmentRule.is_active == True
            ).order_by(desc(AssignmentRule.priority)).all()
            
            # Try each rule in order of priority
            for rule in rules:
                experts = self._get_experts_by_rule(request, rule)
                if experts:
                    # Select the best expert from the filtered list
                    return self._select_best_expert(experts, request)
            
            # If no rules match, use default logic
            return self._get_default_assignment(request)
            
        except Exception as e:
            logger.error(f"Error finding best expert: {e}")
            return None
    
    def _get_experts_by_rule(self, request: ShipmentRequest, rule: AssignmentRule) -> List[ExpertUser]:
        """Get experts based on assignment rule conditions."""
        try:
            conditions = json.loads(rule.conditions)
            rule_type = rule.rule_type
            
            if rule_type == "transport_method":
                return self._filter_by_transport_method(request, conditions)
            elif rule_type == "location":
                return self._filter_by_location(request, conditions)
            elif rule_type == "priority":
                return self._filter_by_priority(request, conditions)
            elif rule_type == "workload":
                return self._filter_by_workload(request, conditions)
            else:
                logger.warning(f"Unknown rule type: {rule_type}")
                return []
                
        except Exception as e:
            logger.error(f"Error applying rule {rule.id}: {e}")
            return []
    
    def _filter_by_transport_method(self, request: ShipmentRequest, conditions: Dict) -> List[ExpertUser]:
        """Filter experts by transport method specialization."""
        transport_method = request.transport_method
        if not transport_method:
            return []
        
        # Find transport method ID
        transport = self.db.query(TransportMethod).filter(
            TransportMethod.name == transport_method
        ).first()
        
        if not transport:
            return []
        
        # Get experts specialized in this transport method
        experts = self.db.query(ExpertUser).join(ExpertSpecialization).filter(
            and_(
                ExpertSpecialization.transport_method_id == transport.id,
                ExpertUser.is_active == True,
                ExpertUser.role.in_(["expert", "business_expert"])
            )
        ).all()
        
        return experts
    
    def _filter_by_location(self, request: ShipmentRequest, conditions: Dict) -> List[ExpertUser]:
        """Filter experts by location preferences."""
        # This can be extended based on location-based rules
        # For now, return all active experts
        return self.db.query(ExpertUser).filter(
            and_(
                ExpertUser.is_active == True,
                ExpertUser.role.in_(["expert", "business_expert"])
            )
        ).all()
    
    def _filter_by_priority(self, request: ShipmentRequest, conditions: Dict) -> List[ExpertUser]:
        """Filter experts by priority handling capability."""
        priority = request.priority or "normal"
        
        # Get experts who can handle this priority level
        experts = self.db.query(ExpertUser).filter(
            and_(
                ExpertUser.is_active == True,
                ExpertUser.role.in_(["expert", "business_expert"])
            )
        ).all()
        
        # Filter by priority handling capability (can be extended)
        return experts
    
    def _filter_by_workload(self, request: ShipmentRequest, conditions: Dict) -> List[ExpertUser]:
        """Filter experts by current workload."""
        max_workload = conditions.get("max_workload", 10)
        
        # Get experts with workload below threshold
        experts = self.db.query(ExpertUser).filter(
            and_(
                ExpertUser.is_active == True,
                ExpertUser.role.in_(["expert", "business_expert"])
            )
        ).all()
        
        # Filter by workload
        suitable_experts = []
        for expert in experts:
            if expert.get_workload() < max_workload:
                suitable_experts.append(expert)
        
        return suitable_experts
    
    def _select_best_expert(self, experts: List[ExpertUser], request: ShipmentRequest) -> Optional[int]:
        """
        Select the best expert from a list of candidates with fairness consideration.
        
        Uses weighted scoring with round-robin fallback for fairness.
        If multiple experts have similar scores (within 5 points), 
        prefer the one with lower recent assignment count for fairness.
        """
        if not experts:
            return None
        
        # Filter out inactive experts
        active_experts = [e for e in experts if e.is_active]
        if not active_experts:
            logger.warning("No active experts available for assignment")
            return None
        
        # Score experts
        scored_experts = []
        for expert in active_experts:
            score = self._calculate_expert_score(expert, request)
            workload = expert.get_workload()
            
            # Get recent assignment count for fairness (last 24 hours)
            recent_assignments = self.db.query(AssignmentLog).filter(
                and_(
                    AssignmentLog.assigned_expert_id == expert.id,
                    AssignmentLog.created_at >= datetime.utcnow() - timedelta(hours=24)
                )
            ).count()
            
            scored_experts.append({
                'expert': expert,
                'score': score,
                'workload': workload,
                'recent_assignments': recent_assignments
            })
        
        # Sort by score (higher is better)
        scored_experts.sort(key=lambda x: x['score'], reverse=True)
        
        if not scored_experts:
            return None
        
        # If top expert has significantly higher score (>5 points), use them
        top_score = scored_experts[0]['score']
        top_experts = [e for e in scored_experts if top_score - e['score'] <= 5]
        
        if len(top_experts) == 1:
            # Clear winner
            return top_experts[0]['expert'].id
        
        # Multiple experts with similar scores - use fairness (round-robin)
        # Select expert with lowest recent assignments
        best_expert = min(top_experts, key=lambda x: (
            x['recent_assignments'],
            x['workload']
        ))
        
        return best_expert['expert'].id
    
    def _calculate_expert_score(self, expert: ExpertUser, request: ShipmentRequest) -> float:
        """
        Calculate weighted score for expert suitability.
        
        Scoring factors:
        - Proficiency level: expert=30, advanced=20, intermediate=15, beginner=10
        - Primary specialization bonus: +20
        - Workload penalty: -2 per request (max penalty: -30)
        - Role bonus: business_expert=+5, expert=+3
        - Recent activity: +5 if active in last 7 days, +2 if in last 30 days
        
        Returns weighted score (higher is better).
        """
        score = 0.0
        
        # Base score for being active (required)
        if not expert.is_active:
            return -1000.0  # Inactive experts should never be selected
        
        score += 10.0
        
        # Workload factor (lower workload = higher score)
        # Penalty: -2 points per active request, capped at -30
        workload = expert.get_workload()
        workload_penalty = min(workload * 2, 30)
        score += max(0, 30.0 - workload_penalty)
        
        # Specialization and proficiency factor
        transport_method_name = (
            request.domestic_transport_method or 
            request.international_transport_method or 
            request.transport_method
        )
        
        if transport_method_name:
            transport = self.db.query(TransportMethod).filter(
                or_(
                    TransportMethod.name == transport_method_name,
                    TransportMethod.name_fa == transport_method_name
                )
            ).first()
            
            if transport:
                # Check if expert has specialization for this transport method
                matching_spec = None
                for spec in expert.specializations:
                    if spec.transport_method_id == transport.id:
                        matching_spec = spec
                        break
                
                if matching_spec:
                    # Proficiency level scoring
                    proficiency_scores = {
                        'expert': 30.0,
                        'advanced': 20.0,
                        'intermediate': 15.0,
                        'beginner': 10.0
                    }
                    proficiency = matching_spec.proficiency_level or 'intermediate'
                    score += proficiency_scores.get(proficiency, 15.0)
                    
                    # Primary specialization bonus
                    if matching_spec.is_primary:
                        score += 20.0
                else:
                    # No specialization - significant penalty
                    score -= 25.0
        
        # Role factor (business_expert has more experience)
        if expert.role == "business_expert":
            score += 5.0
        elif expert.role == "expert":
            score += 3.0
        
        # Recent activity factor
        if expert.last_login_at:
            days_since_login = (datetime.utcnow() - expert.last_login_at).days
            if days_since_login <= 7:
                score += 5.0
            elif days_since_login <= 30:
                score += 2.0
            elif days_since_login > 90:
                # Penalty for inactive experts
                score -= 10.0
        
        return score
    
    def _get_default_assignment(self, request: ShipmentRequest) -> Optional[int]:
        """Default assignment logic when no rules match."""
        # Get all active experts
        experts = self.db.query(ExpertUser).filter(
            and_(
                ExpertUser.is_active == True,
                ExpertUser.role.in_(["expert", "business_expert"])
            )
        ).all()
        
        if not experts:
            return None
        
        # Select expert with lowest workload
        best_expert = min(experts, key=lambda e: e.get_workload())
        return best_expert.id
    
    def _assign_to_expert(self, request: ShipmentRequest, expert_id: int, assignment_method: str, reason: str = None):
        """
        Assign request to expert and create log entry with detailed reason.
        
        Args:
            request: ShipmentRequest to assign
            expert_id: ID of expert to assign to
            assignment_method: "automatic", "manual", or "override"
            reason: Detailed reason for assignment (auto-generated if not provided)
        """
        try:
            expert = self.db.query(ExpertUser).get(expert_id)
            if not expert or not expert.is_active:
                raise ValueError(f"Expert {expert_id} is not active or does not exist")
            
            # Update request
            request.assigned_to = expert_id
            request.status = "assigned"
            request.has_unread_for_assignee = True
            
            # Generate detailed assignment reason if not provided
            if not reason:
                workload = expert.get_workload()
                transport_method = (
                    request.domestic_transport_method or 
                    request.international_transport_method or 
                    request.transport_method or 
                    "unknown"
                )
                
                # Check specialization match
                specialization_match = False
                primary_match = False
                proficiency = None
                
                if transport_method != "unknown":
                    transport = self.db.query(TransportMethod).filter(
                        or_(
                            TransportMethod.name == transport_method,
                            TransportMethod.name_fa == transport_method
                        )
                    ).first()
                    
                    if transport:
                        for spec in expert.specializations:
                            if spec.transport_method_id == transport.id:
                                specialization_match = True
                                proficiency = spec.proficiency_level
                                if spec.is_primary:
                                    primary_match = True
                                break
                
                reason_parts = []
                if assignment_method == "automatic":
                    reason_parts.append("ارجاع خودکار")
                    if specialization_match:
                        reason_parts.append(f"تخصص در {transport_method}")
                        if primary_match:
                            reason_parts.append("(تخصص اصلی)")
                        if proficiency:
                            reason_parts.append(f"سطح مهارت: {proficiency}")
                    reason_parts.append(f"بار کاری: {workload}")
                else:
                    reason_parts.append(f"ارجاع {assignment_method}")
                
                reason = " - ".join(reason_parts)
            
            # Create assignment log
            log = AssignmentLog(
                shipment_request_id=request.id,
                assigned_expert_id=expert_id,
                assignment_method=assignment_method,
                assignment_reason=reason,
                created_at=datetime.utcnow()
            )
            self.db.add(log)
            
            # Create notification for expert
            self._create_assignment_notification(expert_id, request.id)
            
            # Handle gamification for expert assignment
            if request.gamification_customer_id:
                try:
                    # Create workflow step for expert assignment
                    workflow_step = CustomerWorkflowStep(
                        customer_id=request.gamification_customer_id,
                        shipment_request_id=request.id,
                        step_name="expert_assigned",
                        step_order=3,
                        is_completed=True,
                        completed_at=datetime.utcnow(),
                        points_earned=15
                    )
                    self.db.add(workflow_step)
                    
                    # Update customer loyalty points
                    customer = self.db.query(CustomerGamification).filter(
                        CustomerGamification.id == request.gamification_customer_id
                    ).first()
                    
                    if customer:
                        customer.update_loyalty_points(15)
                        logger.info(f"Gamification: Customer {request.gamification_customer_id} got expert assigned for request {request.id}, earned 15 points")
                        
                except Exception as e:
                    logger.error(f"Error in gamification for expert assignment: {e}")
                    # Don't fail the assignment if gamification fails
            
            # Commit changes
            self.db.commit()
            
            logger.info(f"Request {request.id} assigned to expert {expert_id} ({expert.full_name}) - Method: {assignment_method}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error assigning request {request.id} to expert {expert_id}: {e}")
            raise
    
    def _create_assignment_notification(self, expert_id: int, request_id: int):
        """Create notification for expert when request is assigned."""
        try:
            from backend.models import ExpertConsoleNotification
            
            notification = ExpertConsoleNotification(
                expert_user_id=expert_id,
                shipment_request_id=request_id,
                notification_type="request_assigned",
                title="درخواست جدید ارجاع داده شد",
                message=f"یک درخواست حمل و نقل جدید به شما ارجاع داده شد.",
                is_read=False,
                created_at=datetime.utcnow()
            )
            self.db.add(notification)
            # Note: Don't commit here, let the caller commit
            
        except Exception as e:
            logger.error(f"Error creating assignment notification: {e}")
            # Don't fail assignment if notification fails
    
    def get_assignment_statistics(self) -> Dict[str, Any]:
        """Get statistics about assignment performance."""
        try:
            # Total assignments
            total_assignments = self.db.query(AssignmentLog).count()
            
            # Automatic vs manual assignments
            automatic_count = self.db.query(AssignmentLog).filter(
                AssignmentLog.assignment_method == "automatic"
            ).count()
            
            manual_count = self.db.query(AssignmentLog).filter(
                AssignmentLog.assignment_method == "manual"
            ).count()
            
            # Expert workload distribution
            expert_workloads = []
            experts = self.db.query(ExpertUser).filter(
                ExpertUser.is_active == True
            ).all()
            
            for expert in experts:
                workload = expert.get_workload()
                expert_workloads.append({
                    "expert_id": expert.id,
                    "expert_name": expert.full_name,
                    "workload": workload
                })
            
            return {
                "total_assignments": total_assignments,
                "automatic_assignments": automatic_count,
                "manual_assignments": manual_count,
                "expert_workloads": expert_workloads
            }
            
        except Exception as e:
            logger.error(f"Error getting assignment statistics: {e}")
            return {}


# Global instance
assignment_engine = AssignmentEngine()
