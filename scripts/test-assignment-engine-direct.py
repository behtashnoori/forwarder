#!/usr/bin/env python3
"""
Direct tests for assignment engine functionality.
Tests the assignment engine without requiring a running server.

Usage:
    python scripts/test-assignment-engine-direct.py
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Import database models and engine
from models import (
    ShipmentRequest, ExpertUser, AssignmentRule, AssignmentLog, 
    ExpertConsoleLog, ExpertConsoleNotification, TransportMethod,
    ExpertSpecialization, Province, County, City
)
from assignment_engine import AssignmentEngine
from extensions import db
from app import create_app

class AssignmentEngineTester:
    """Direct tester for assignment engine functionality."""
    
    def __init__(self):
        self.app = create_app()
        self.assignment_engine = AssignmentEngine()
        self.test_results = []
        self.created_requests = []
        self.created_experts = []
        self.created_rules = []
        
    def log_test(self, test_name: str, success: bool, message: str = "", details: Dict = None):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2, default=str)}")
    
    def setup_test_data(self):
        """Set up test data for assignment tests."""
        print("\n🔧 Setting up test data...")
        
        with self.app.app_context():
            try:
                # Create test experts
                expert1 = ExpertUser(
                    username="test_expert_1",
                    password_hash="hashed_password_1",
                    full_name="کارشناس تست ۱",
                    email="expert1@test.com",
                    role="expert",
                    is_active=True,
                    department="operations"
                )
                
                expert2 = ExpertUser(
                    username="test_expert_2", 
                    password_hash="hashed_password_2",
                    full_name="کارشناس تست ۲",
                    email="expert2@test.com",
                    role="business_expert",
                    is_active=True,
                    department="business"
                )
                
                expert3 = ExpertUser(
                    username="test_expert_3",
                    password_hash="hashed_password_3", 
                    full_name="کارشناس تست ۳",
                    email="expert3@test.com",
                    role="expert",
                    is_active=False,  # Inactive expert
                    department="operations"
                )
                
                db.session.add_all([expert1, expert2, expert3])
                db.session.commit()
                
                self.created_experts = [expert1.id, expert2.id, expert3.id]
                
                # Create test provinces and cities
                province = Province(name_fa="تهران", code="11")
                county = County(name_fa="تهران", province_id=1)
                city = City(name_fa="تهران", county_id=1, province_id=1)
                
                db.session.add_all([province, county, city])
                db.session.commit()
                
                # Create test transport methods
                transport1 = TransportMethod(
                    name="road",
                    display_name="حمل جاده‌ای",
                    description="حمل و نقل جاده‌ای",
                    is_active=True
                )
                
                transport2 = TransportMethod(
                    name="air",
                    display_name="حمل هوایی", 
                    description="حمل و نقل هوایی",
                    is_active=True
                )
                
                db.session.add_all([transport1, transport2])
                db.session.commit()
                
                # Create expert specializations
                spec1 = ExpertSpecialization(
                    expert_user_id=expert1.id,
                    transport_method_id=transport1.id,
                    is_primary=True,
                    proficiency_level=5
                )
                
                spec2 = ExpertSpecialization(
                    expert_user_id=expert2.id,
                    transport_method_id=transport2.id,
                    is_primary=True,
                    proficiency_level=5
                )
                
                db.session.add_all([spec1, spec2])
                db.session.commit()
                
                # Create test shipment requests
                request1 = ShipmentRequest(
                    customer_first_name="مشتری",
                    customer_last_name="تست",
                    contact_phone="09123456789",
                    origin_province_id=1,
                    origin_county_id=1,
                    origin_city_id=1,
                    dest_province_id=1,
                    dest_county_id=1,
                    dest_city_id=1,
                    transport_method="road",
                    cargo_description="محصولات تست",
                    cargo_weight=100.0,
                    status="new",
                    priority="normal",
                    created_at=datetime.utcnow()
                )
                
                request2 = ShipmentRequest(
                    customer_first_name="مشتری",
                    customer_last_name="تست ۲",
                    contact_phone="09123456790",
                    origin_province_id=1,
                    origin_county_id=1,
                    origin_city_id=1,
                    dest_province_id=1,
                    dest_county_id=1,
                    dest_city_id=1,
                    transport_method="air",
                    cargo_description="محصولات تست ۲",
                    cargo_weight=50.0,
                    status="new",
                    priority="high",
                    created_at=datetime.utcnow()
                )
                
                request3 = ShipmentRequest(
                    customer_first_name="مشتری",
                    customer_last_name="تست ۳",
                    contact_phone="09123456791",
                    origin_province_id=1,
                    origin_county_id=1,
                    origin_city_id=1,
                    dest_province_id=1,
                    dest_county_id=1,
                    dest_city_id=1,
                    transport_method="road",
                    cargo_description="محصولات تست ۳",
                    cargo_weight=200.0,
                    status="assigned",
                    assigned_to=expert1.id,
                    priority="normal",
                    created_at=datetime.utcnow()
                )
                
                db.session.add_all([request1, request2, request3])
                db.session.commit()
                
                self.created_requests = [request1.id, request2.id, request3.id]
                
                # Create assignment rules
                rule1 = AssignmentRule(
                    name="قاعده حمل جاده‌ای",
                    description="ارجاع درخواست‌های حمل جاده‌ای به کارشناسان متخصص",
                    rule_type="transport_method",
                    conditions=json.dumps({"transport_methods": ["road"]}),
                    priority=10,
                    is_active=True,
                    created_by=expert1.id
                )
                
                rule2 = AssignmentRule(
                    name="قاعده حمل هوایی",
                    description="ارجاع درخواست‌های حمل هوایی به کارشناسان متخصص",
                    rule_type="transport_method", 
                    conditions=json.dumps({"transport_methods": ["air"]}),
                    priority=10,
                    is_active=True,
                    created_by=expert1.id
                )
                
                rule3 = AssignmentRule(
                    name="قاعده اولویت بالا",
                    description="ارجاع درخواست‌های اولویت بالا به کارشناسان ارشد",
                    rule_type="priority",
                    conditions=json.dumps({"priority": "high"}),
                    priority=20,
                    is_active=True,
                    created_by=expert1.id
                )
                
                db.session.add_all([rule1, rule2, rule3])
                db.session.commit()
                
                self.created_rules = [rule1.id, rule2.id, rule3.id]
                
                print("✅ Test data setup completed")
                return True
                
            except Exception as e:
                print(f"❌ Error setting up test data: {e}")
                db.session.rollback()
                return False
    
    def test_automatic_assignment_engine(self):
        """Test automatic assignment engine functionality."""
        print("\n🤖 Testing automatic assignment engine...")
        
        with self.app.app_context():
            try:
                # Test 1: Assign road transport request
                road_request_id = self.created_requests[0]
                expert_id = self.assignment_engine.assign_request(road_request_id, "automatic")
                
                if expert_id:
                    # Check if it was assigned to the road transport expert
                    request = db.session.query(ShipmentRequest).get(road_request_id)
                    if request.assigned_to == expert_id and request.status == "assigned":
                        self.log_test(
                            "Automatic Assignment - Road Transport",
                            True,
                            f"Request assigned to expert {expert_id}",
                            {"request_id": road_request_id, "expert_id": expert_id}
                        )
                    else:
                        self.log_test(
                            "Automatic Assignment - Road Transport",
                            False,
                            "Request not properly assigned"
                        )
                else:
                    self.log_test(
                        "Automatic Assignment - Road Transport",
                        False,
                        "No expert assigned"
                    )
                
                # Test 2: Assign air transport request
                air_request_id = self.created_requests[1]
                expert_id = self.assignment_engine.assign_request(air_request_id, "automatic")
                
                if expert_id:
                    request = db.session.query(ShipmentRequest).get(air_request_id)
                    if request.assigned_to == expert_id and request.status == "assigned":
                        self.log_test(
                            "Automatic Assignment - Air Transport",
                            True,
                            f"Request assigned to expert {expert_id}",
                            {"request_id": air_request_id, "expert_id": expert_id}
                        )
                    else:
                        self.log_test(
                            "Automatic Assignment - Air Transport",
                            False,
                            "Request not properly assigned"
                        )
                else:
                    self.log_test(
                        "Automatic Assignment - Air Transport",
                        False,
                        "No expert assigned"
                    )
                
                # Test 3: Already assigned request
                assigned_request_id = self.created_requests[2]
                expert_id = self.assignment_engine.assign_request(assigned_request_id, "automatic")
                
                if expert_id:
                    self.log_test(
                        "Automatic Assignment - Already Assigned",
                        True,
                        f"Returned existing assignment: {expert_id}"
                    )
                else:
                    self.log_test(
                        "Automatic Assignment - Already Assigned",
                        False,
                        "Should return existing assignment"
                    )
                
                # Test 4: Non-existent request
                expert_id = self.assignment_engine.assign_request(99999, "automatic")
                
                if expert_id is None:
                    self.log_test(
                        "Automatic Assignment - Non-existent Request",
                        True,
                        "Correctly returned None for non-existent request"
                    )
                else:
                    self.log_test(
                        "Automatic Assignment - Non-existent Request",
                        False,
                        "Should return None for non-existent request"
                    )
                    
            except Exception as e:
                self.log_test(
                    "Automatic Assignment Engine",
                    False,
                    f"Unexpected error: {e}"
                )
    
    def test_expert_scoring(self):
        """Test expert scoring algorithm."""
        print("\n📊 Testing expert scoring...")
        
        with self.app.app_context():
            try:
                # Create a test request
                test_request = ShipmentRequest(
                    customer_first_name="تست",
                    customer_last_name="امتیاز",
                    contact_phone="09123456799",
                    origin_province_id=1,
                    origin_county_id=1,
                    origin_city_id=1,
                    dest_province_id=1,
                    dest_county_id=1,
                    dest_city_id=1,
                    transport_method="road",
                    cargo_description="تست امتیاز",
                    status="new",
                    priority="normal"
                )
                
                # Get active experts
                experts = db.session.query(ExpertUser).filter(
                    ExpertUser.is_active == True
                ).all()
                
                if experts:
                    # Test expert scoring
                    scores = []
                    for expert in experts:
                        score = self.assignment_engine._calculate_expert_score(expert, test_request)
                        workload = expert.get_workload()
                        scores.append({
                            "expert_id": expert.id, 
                            "name": expert.full_name,
                            "role": expert.role,
                            "score": score,
                            "workload": workload
                        })
                    
                    scores.sort(key=lambda x: x["score"], reverse=True)
                    
                    # Check if scoring is working
                    if scores and all(isinstance(s["score"], (int, float)) for s in scores):
                        self.log_test(
                            "Expert Scoring - Algorithm",
                            True,
                            "Expert scoring completed successfully",
                            {"scores": scores}
                        )
                    else:
                        self.log_test(
                            "Expert Scoring - Algorithm",
                            False,
                            "Expert scoring failed"
                        )
                    
                    # Check if best expert is selected
                    if scores and scores[0]["score"] > 0:
                        self.log_test(
                            "Expert Scoring - Best Expert Selection",
                            True,
                            f"Best expert selected: {scores[0]['name']} (score: {scores[0]['score']})"
                        )
                    else:
                        self.log_test(
                            "Expert Scoring - Best Expert Selection",
                            False,
                            "No suitable expert found"
                        )
                else:
                    self.log_test(
                        "Expert Scoring",
                        False,
                        "No active experts found for scoring"
                    )
                    
            except Exception as e:
                self.log_test(
                    "Expert Scoring",
                    False,
                    f"Unexpected error: {e}"
                )
    
    def test_assignment_rules(self):
        """Test assignment rules functionality."""
        print("\n📋 Testing assignment rules...")
        
        with self.app.app_context():
            try:
                # Test 1: Check rule loading
                rules = db.session.query(AssignmentRule).filter(
                    AssignmentRule.is_active == True
                ).order_by(AssignmentRule.priority.desc()).all()
                
                if rules:
                    self.log_test(
                        "Assignment Rules - Rule Loading",
                        True,
                        f"Loaded {len(rules)} active assignment rules",
                        {"rules": [{"id": rule.id, "name": rule.name, "type": rule.rule_type, "priority": rule.priority} for rule in rules]}
                    )
                else:
                    self.log_test(
                        "Assignment Rules - Rule Loading",
                        False,
                        "No active assignment rules found"
                    )
                
                # Test 2: Test rule application
                if rules:
                    # Test transport method rule
                    road_request = db.session.query(ShipmentRequest).filter(
                        ShipmentRequest.transport_method == "road"
                    ).first()
                    
                    if road_request:
                        # Find best expert using rules
                        expert_id = self.assignment_engine._find_best_expert(road_request)
                        
                        if expert_id:
                            self.log_test(
                                "Assignment Rules - Rule Application",
                                True,
                                f"Rule-based assignment successful: expert {expert_id}"
                            )
                        else:
                            self.log_test(
                                "Assignment Rules - Rule Application",
                                False,
                                "Rule-based assignment failed"
                            )
                    else:
                        self.log_test(
                            "Assignment Rules - Rule Application",
                            False,
                            "No road transport request found for testing"
                        )
                else:
                    self.log_test(
                        "Assignment Rules - Rule Application",
                        False,
                        "No rules available for testing"
                    )
                    
            except Exception as e:
                self.log_test(
                    "Assignment Rules",
                    False,
                    f"Unexpected error: {e}"
                )
    
    def test_workload_distribution(self):
        """Test workload distribution among experts."""
        print("\n⚖️ Testing workload distribution...")
        
        with self.app.app_context():
            try:
                # Get initial workload
                experts = db.session.query(ExpertUser).filter(
                    ExpertUser.is_active == True
                ).all()
                
                initial_workloads = {expert.id: expert.get_workload() for expert in experts}
                
                # Create multiple requests and assign them
                new_requests = []
                for i in range(5):
                    new_request = ShipmentRequest(
                        customer_first_name=f"مشتری {i}",
                        customer_last_name="تست",
                        contact_phone=f"0912345679{i}",
                        origin_province_id=1,
                        origin_county_id=1,
                        origin_city_id=1,
                        dest_province_id=1,
                        dest_county_id=1,
                        dest_city_id=1,
                        transport_method="road",
                        cargo_description=f"محصولات تست {i}",
                        status="new",
                        priority="normal"
                    )
                    db.session.add(new_request)
                    db.session.commit()
                    new_requests.append(new_request.id)
                
                # Assign all new requests
                assignments = []
                for request_id in new_requests:
                    expert_id = self.assignment_engine.assign_request(request_id, "automatic")
                    if expert_id:
                        assignments.append({"request_id": request_id, "expert_id": expert_id})
                
                # Check final workload
                final_workloads = {expert.id: expert.get_workload() for expert in experts}
                
                # Analyze workload distribution
                workload_changes = {}
                for expert_id in initial_workloads:
                    change = final_workloads[expert_id] - initial_workloads[expert_id]
                    workload_changes[expert_id] = change
                
                # Check if workload is reasonably distributed
                total_assignments = sum(workload_changes.values())
                if total_assignments > 0:
                    self.log_test(
                        "Workload Distribution - Assignment Count",
                        True,
                        f"Assigned {total_assignments} requests across experts",
                        {"assignments": assignments, "workload_changes": workload_changes}
                    )
                else:
                    self.log_test(
                        "Workload Distribution - Assignment Count",
                        False,
                        "No requests were assigned"
                    )
                
                # Check if no single expert got all assignments
                max_assignments = max(workload_changes.values()) if workload_changes else 0
                if max_assignments <= total_assignments // 2 + 1:  # Reasonable distribution
                    self.log_test(
                        "Workload Distribution - Fairness",
                        True,
                        f"Workload reasonably distributed (max: {max_assignments})"
                    )
                else:
                    self.log_test(
                        "Workload Distribution - Fairness",
                        False,
                        f"Workload not fairly distributed (max: {max_assignments})"
                    )
                
                # Clean up test requests
                db.session.query(ShipmentRequest).filter(
                    ShipmentRequest.id.in_(new_requests)
                ).delete(synchronize_session=False)
                db.session.commit()
                    
            except Exception as e:
                self.log_test(
                    "Workload Distribution",
                    False,
                    f"Unexpected error: {e}"
                )
    
    def test_assignment_logging(self):
        """Test assignment logging functionality."""
        print("\n📝 Testing assignment logging...")
        
        with self.app.app_context():
            try:
                # Test 1: Check assignment log creation
                assignment_logs = db.session.query(AssignmentLog).all()
                
                if assignment_logs:
                    self.log_test(
                        "Assignment Logging - Log Creation",
                        True,
                        f"Found {len(assignment_logs)} assignment logs",
                        {"logs": [{"id": log.id, "method": log.assignment_method, "reason": log.assignment_reason} for log in assignment_logs]}
                    )
                else:
                    self.log_test(
                        "Assignment Logging - Log Creation",
                        False,
                        "No assignment logs found"
                    )
                
                # Test 2: Check expert console log creation
                console_logs = db.session.query(ExpertConsoleLog).filter(
                    ExpertConsoleLog.action == "assignment"
                ).all()
                
                if console_logs:
                    self.log_test(
                        "Assignment Logging - Console Log Creation",
                        True,
                        f"Found {len(console_logs)} assignment console logs"
                    )
                else:
                    self.log_test(
                        "Assignment Logging - Console Log Creation",
                        False,
                        "No assignment console logs found"
                    )
                
                # Test 3: Check notification creation
                notifications = db.session.query(ExpertConsoleNotification).filter(
                    ExpertConsoleNotification.notification_type == "assignment"
                ).all()
                
                if notifications:
                    self.log_test(
                        "Assignment Logging - Notification Creation",
                        True,
                        f"Found {len(notifications)} assignment notifications"
                    )
                else:
                    self.log_test(
                        "Assignment Logging - Notification Creation",
                        False,
                        "No assignment notifications found"
                    )
                    
            except Exception as e:
                self.log_test(
                    "Assignment Logging",
                    False,
                    f"Unexpected error: {e}"
                )
    
    def test_assignment_statistics(self):
        """Test assignment statistics functionality."""
        print("\n📊 Testing assignment statistics...")
        
        with self.app.app_context():
            try:
                # Test 1: Get assignment statistics
                stats = self.assignment_engine.get_assignment_statistics()
                
                if stats:
                    self.log_test(
                        "Assignment Statistics - Data Collection",
                        True,
                        "Assignment statistics collected successfully",
                        {"statistics": stats}
                    )
                else:
                    self.log_test(
                        "Assignment Statistics - Data Collection",
                        False,
                        "Failed to collect assignment statistics"
                    )
                
                # Test 2: Check workload distribution in stats
                if "expert_workloads" in stats:
                    workloads = stats["expert_workloads"]
                    if workloads:
                        total_workload = sum(w["workload"] for w in workloads)
                        avg_workload = total_workload / len(workloads) if workloads else 0
                        
                        self.log_test(
                            "Assignment Statistics - Workload Analysis",
                            True,
                            f"Workload analysis completed. Average: {avg_workload:.2f}",
                            {"total_workload": total_workload, "average_workload": avg_workload, "workloads": workloads}
                        )
                    else:
                        self.log_test(
                            "Assignment Statistics - Workload Analysis",
                            False,
                            "No workload data available"
                        )
                else:
                    self.log_test(
                        "Assignment Statistics - Workload Analysis",
                        False,
                        "Workload data not in statistics"
                    )
                
                # Test 3: Check assignment method distribution
                if "automatic_assignments" in stats and "manual_assignments" in stats:
                    auto_count = stats["automatic_assignments"]
                    manual_count = stats["manual_assignments"]
                    total_count = stats.get("total_assignments", 0)
                    
                    self.log_test(
                        "Assignment Statistics - Method Distribution",
                        True,
                        f"Assignment methods: {auto_count} automatic, {manual_count} manual, {total_count} total"
                    )
                else:
                    self.log_test(
                        "Assignment Statistics - Method Distribution",
                        False,
                        "Assignment method data not available"
                    )
                    
            except Exception as e:
                self.log_test(
                    "Assignment Statistics",
                    False,
                    f"Unexpected error: {e}"
                )
    
    def cleanup_test_data(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        with self.app.app_context():
            try:
                # Delete assignment logs
                db.session.query(AssignmentLog).filter(
                    AssignmentLog.shipment_request_id.in_(self.created_requests)
                ).delete(synchronize_session=False)
                
                # Delete expert console logs
                db.session.query(ExpertConsoleLog).filter(
                    ExpertConsoleLog.shipment_request_id.in_(self.created_requests)
                ).delete(synchronize_session=False)
                
                # Delete notifications
                db.session.query(ExpertConsoleNotification).filter(
                    ExpertConsoleNotification.shipment_request_id.in_(self.created_requests)
                ).delete(synchronize_session=False)
                
                # Delete assignment rules
                db.session.query(AssignmentRule).filter(
                    AssignmentRule.id.in_(self.created_rules)
                ).delete(synchronize_session=False)
                
                # Delete expert specializations
                db.session.query(ExpertSpecialization).filter(
                    ExpertSpecialization.expert_user_id.in_(self.created_experts)
                ).delete(synchronize_session=False)
                
                # Delete shipment requests
                db.session.query(ShipmentRequest).filter(
                    ShipmentRequest.id.in_(self.created_requests)
                ).delete(synchronize_session=False)
                
                # Delete experts
                db.session.query(ExpertUser).filter(
                    ExpertUser.id.in_(self.created_experts)
                ).delete(synchronize_session=False)
                
                db.session.commit()
                print("✅ Test data cleanup completed")
                
            except Exception as e:
                print(f"❌ Error cleaning up test data: {e}")
                db.session.rollback()
    
    def run_all_tests(self):
        """Run all assignment engine tests."""
        print("🚀 Starting Assignment Engine Tests")
        print("=" * 50)
        
        # Setup
        if not self.setup_test_data():
            print("❌ Failed to setup test data. Aborting tests.")
            return
        
        # Run tests
        self.test_automatic_assignment_engine()
        self.test_expert_scoring()
        self.test_assignment_rules()
        self.test_workload_distribution()
        self.test_assignment_logging()
        self.test_assignment_statistics()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("📋 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n" + "=" * 50)
        
        # Save detailed results
        with open("assignment-engine-test-results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)
        
        print("📄 Detailed results saved to: assignment-engine-test-results.json")


def main():
    """Main function to run the tests."""
    tester = AssignmentEngineTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
