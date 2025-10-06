"""Automatic assignment engine for shipment requests."""
import json
import logging
from datetime import datetime
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
    
    def assign_request(self, request_id: int, assignment_method: str = "automatic") -> Optional[int]:
        """
        Assign a shipment request to the most suitable expert.
        
        Args:
            request_id: ID of the shipment request
            assignment_method: "automatic", "manual", or "override"
            
        Returns:
            ID of assigned expert or None if no suitable expert found
        """
        try:
            # Get the shipment request
            request = self.db.query(ShipmentRequest).get(request_id)
            if not request:
                logger.error(f"Shipment request {request_id} not found")
                return None
            
            # Skip if already assigned
            if request.assigned_to:
                logger.info(f"Request {request_id} already assigned to expert {request.assigned_to}")
                return request.assigned_to
            
            # Find the best expert
            expert_id = self._find_best_expert(request)
            
            if expert_id:
                # Assign the request
                self._assign_to_expert(request, expert_id, assignment_method)
                logger.info(f"Request {request_id} assigned to expert {expert_id}")
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
        """Select the best expert from a list of candidates."""
        if not experts:
            return None
        
        # Score experts based on multiple criteria
        scored_experts = []
        
        for expert in experts:
            score = self._calculate_expert_score(expert, request)
            scored_experts.append((expert, score))
        
        # Sort by score (higher is better)
        scored_experts.sort(key=lambda x: x[1], reverse=True)
        
        # Return the best expert
        return scored_experts[0][0].id if scored_experts else None
    
    def _calculate_expert_score(self, expert: ExpertUser, request: ShipmentRequest) -> float:
        """Calculate a score for expert suitability."""
        score = 0.0
        
        # Base score for being active
        if expert.is_active:
            score += 10.0
        
        # Workload factor (lower workload = higher score)
        workload = expert.get_workload()
        score += max(0, 20.0 - workload * 2)
        
        # Specialization factor
        if request.transport_method:
            transport = self.db.query(TransportMethod).filter(
                TransportMethod.name == request.transport_method
            ).first()
            
            if transport and expert.can_handle_transport_method(transport.id):
                score += 15.0
                
                # Check if it's primary specialization
                for spec in expert.specializations:
                    if (spec.transport_method_id == transport.id and 
                        spec.is_primary):
                        score += 10.0
                        break
        
        # Experience factor (based on role)
        if expert.role == "business_expert":
            score += 5.0
        elif expert.role == "expert":
            score += 3.0
        
        # Recent activity factor (can be extended)
        if expert.last_login_at:
            days_since_login = (datetime.utcnow() - expert.last_login_at).days
            if days_since_login <= 7:
                score += 5.0
            elif days_since_login <= 30:
                score += 2.0
        
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
    
    def _assign_to_expert(self, request: ShipmentRequest, expert_id: int, assignment_method: str):
        """Assign request to expert and create log entry."""
        try:
            # Update request
            request.assigned_to = expert_id
            request.status = "assigned"
            request.has_unread_for_assignee = True
            
            # Create assignment log
            log = AssignmentLog(
                shipment_request_id=request.id,
                assigned_expert_id=expert_id,
                assignment_method=assignment_method,
                assignment_reason=f"Automatic assignment based on {assignment_method} logic",
                created_at=datetime.utcnow()
            )
            self.db.add(log)
            
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
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error assigning request {request.id} to expert {expert_id}: {e}")
            raise
    
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
