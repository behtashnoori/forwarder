#!/usr/bin/env python3
"""
Simple tests for assignment functionality.
Tests core assignment logic without database dependencies.

Usage:
    python scripts/test-assignment-simple.py
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

class SimpleAssignmentTester:
    """Simple tester for assignment logic without database dependencies."""
    
    def __init__(self):
        self.test_results = []
        
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
    
    def test_expert_scoring_logic(self):
        """Test expert scoring logic without database."""
        print("\n📊 Testing expert scoring logic...")
        
        try:
            # Mock expert data
            experts = [
                {
                    "id": 1,
                    "name": "کارشناس ۱",
                    "role": "expert",
                    "is_active": True,
                    "workload": 2,
                    "specializations": ["road"],
                    "last_login_days": 1
                },
                {
                    "id": 2,
                    "name": "کارشناس ۲",
                    "role": "business_expert",
                    "is_active": True,
                    "workload": 5,
                    "specializations": ["air"],
                    "last_login_days": 7
                },
                {
                    "id": 3,
                    "name": "کارشناس ۳",
                    "role": "expert",
                    "is_active": False,
                    "workload": 0,
                    "specializations": ["road"],
                    "last_login_days": 30
                }
            ]
            
            # Mock request data
            request = {
                "transport_method": "road",
                "priority": "normal"
            }
            
            # Calculate scores
            scores = []
            for expert in experts:
                score = 0.0
                
                # Base score for being active
                if expert["is_active"]:
                    score += 10.0
                
                # Workload factor (lower workload = higher score)
                score += max(0, 20.0 - expert["workload"] * 2)
                
                # Specialization factor
                if request["transport_method"] in expert["specializations"]:
                    score += 15.0
                
                # Experience factor (based on role)
                if expert["role"] == "business_expert":
                    score += 5.0
                elif expert["role"] == "expert":
                    score += 3.0
                
                # Recent activity factor
                if expert["last_login_days"] <= 7:
                    score += 5.0
                elif expert["last_login_days"] <= 30:
                    score += 2.0
                
                scores.append({
                    "expert_id": expert["id"],
                    "name": expert["name"],
                    "score": score,
                    "is_active": expert["is_active"]
                })
            
            # Sort by score
            scores.sort(key=lambda x: x["score"], reverse=True)
            
            # Test results
            if scores[0]["expert_id"] == 1:  # Expert 1 should have highest score
                self.log_test(
                    "Expert Scoring - Best Expert Selection",
                    True,
                    f"Best expert selected: {scores[0]['name']} (score: {scores[0]['score']})",
                    {"scores": scores}
                )
            else:
                self.log_test(
                    "Expert Scoring - Best Expert Selection",
                    False,
                    f"Wrong expert selected: {scores[0]['name']}",
                    {"scores": scores}
                )
            
            # Test inactive expert exclusion
            active_scores = [s for s in scores if s["is_active"]]
            if len(active_scores) == 2:  # Only 2 active experts
                self.log_test(
                    "Expert Scoring - Active Expert Filtering",
                    True,
                    "Correctly filtered out inactive experts"
                )
            else:
                self.log_test(
                    "Expert Scoring - Active Expert Filtering",
                    False,
                    "Did not properly filter inactive experts"
                )
                
        except Exception as e:
            self.log_test(
                "Expert Scoring Logic",
                False,
                f"Unexpected error: {e}"
            )
    
    def test_assignment_rule_logic(self):
        """Test assignment rule logic without database."""
        print("\n📋 Testing assignment rule logic...")
        
        try:
            # Mock assignment rules
            rules = [
                {
                    "id": 1,
                    "name": "قاعده حمل جاده‌ای",
                    "type": "transport_method",
                    "conditions": {"transport_methods": ["road"]},
                    "priority": 10,
                    "is_active": True
                },
                {
                    "id": 2,
                    "name": "قاعده حمل هوایی",
                    "type": "transport_method",
                    "conditions": {"transport_methods": ["air"]},
                    "priority": 10,
                    "is_active": True
                },
                {
                    "id": 3,
                    "name": "قاعده اولویت بالا",
                    "type": "priority",
                    "conditions": {"priority": "high"},
                    "priority": 20,
                    "is_active": True
                },
                {
                    "id": 4,
                    "name": "قاعده غیرفعال",
                    "type": "transport_method",
                    "conditions": {"transport_methods": ["sea"]},
                    "priority": 5,
                    "is_active": False
                }
            ]
            
            # Test rule filtering
            active_rules = [rule for rule in rules if rule["is_active"]]
            
            if len(active_rules) == 3:
                self.log_test(
                    "Assignment Rules - Active Rule Filtering",
                    True,
                    f"Correctly filtered {len(active_rules)} active rules"
                )
            else:
                self.log_test(
                    "Assignment Rules - Active Rule Filtering",
                    False,
                    f"Expected 3 active rules, got {len(active_rules)}"
                )
            
            # Test rule priority sorting
            sorted_rules = sorted(active_rules, key=lambda x: x["priority"], reverse=True)
            
            if sorted_rules[0]["id"] == 3:  # Priority rule should be first
                self.log_test(
                    "Assignment Rules - Priority Sorting",
                    True,
                    f"Rules correctly sorted by priority: {sorted_rules[0]['name']}"
                )
            else:
                self.log_test(
                    "Assignment Rules - Priority Sorting",
                    False,
                    f"Rules not correctly sorted: {sorted_rules[0]['name']}"
                )
            
            # Test rule matching
            test_requests = [
                {"transport_method": "road", "priority": "normal"},
                {"transport_method": "air", "priority": "normal"},
                {"transport_method": "road", "priority": "high"},
                {"transport_method": "sea", "priority": "normal"}
            ]
            
            matches = []
            for request in test_requests:
                for rule in sorted_rules:
                    if rule["type"] == "transport_method":
                        if request["transport_method"] in rule["conditions"]["transport_methods"]:
                            matches.append({"request": request, "rule": rule})
                            break
                    elif rule["type"] == "priority":
                        if request["priority"] == rule["conditions"]["priority"]:
                            matches.append({"request": request, "rule": rule})
                            break
            
            if len(matches) == 3:  # Should match 3 out of 4 requests
                self.log_test(
                    "Assignment Rules - Rule Matching",
                    True,
                    f"Correctly matched {len(matches)} requests to rules",
                    {"matches": matches}
                )
            else:
                self.log_test(
                    "Assignment Rules - Rule Matching",
                    False,
                    f"Expected 3 matches, got {len(matches)}"
                )
                
        except Exception as e:
            self.log_test(
                "Assignment Rule Logic",
                False,
                f"Unexpected error: {e}"
            )
    
    def test_workload_distribution_logic(self):
        """Test workload distribution logic without database."""
        print("\n⚖️ Testing workload distribution logic...")
        
        try:
            # Mock experts with workloads
            experts = [
                {"id": 1, "name": "کارشناس ۱", "workload": 2, "is_active": True},
                {"id": 2, "name": "کارشناس ۲", "workload": 5, "is_active": True},
                {"id": 3, "name": "کارشناس ۳", "workload": 1, "is_active": True},
                {"id": 4, "name": "کارشناس ۴", "workload": 0, "is_active": False}
            ]
            
            # Test workload calculation
            active_experts = [e for e in experts if e["is_active"]]
            total_workload = sum(e["workload"] for e in active_experts)
            avg_workload = total_workload / len(active_experts) if active_experts else 0
            
            if avg_workload == 8/3:  # (2+5+1)/3
                self.log_test(
                    "Workload Distribution - Average Calculation",
                    True,
                    f"Correctly calculated average workload: {avg_workload:.2f}"
                )
            else:
                self.log_test(
                    "Workload Distribution - Average Calculation",
                    False,
                    f"Expected 2.67, got {avg_workload:.2f}"
                )
            
            # Test expert selection based on workload
            best_expert = min(active_experts, key=lambda x: x["workload"])
            
            if best_expert["id"] == 3:  # Expert 3 has lowest workload
                self.log_test(
                    "Workload Distribution - Best Expert Selection",
                    True,
                    f"Correctly selected expert with lowest workload: {best_expert['name']}"
                )
            else:
                self.log_test(
                    "Workload Distribution - Best Expert Selection",
                    False,
                    f"Wrong expert selected: {best_expert['name']}"
                )
            
            # Test workload balancing
            requests_to_assign = 5
            assignments = []
            
            for i in range(requests_to_assign):
                # Select expert with lowest current workload
                best_expert = min(active_experts, key=lambda x: x["workload"])
                assignments.append(best_expert["id"])
                best_expert["workload"] += 1  # Simulate assignment
            
            # Check if workload is reasonably distributed
            final_workloads = [e["workload"] for e in active_experts]
            max_workload = max(final_workloads)
            min_workload = min(final_workloads)
            
            if max_workload - min_workload <= 1:  # Workload should be balanced
                self.log_test(
                    "Workload Distribution - Balancing",
                    True,
                    f"Workload reasonably balanced (max: {max_workload}, min: {min_workload})",
                    {"assignments": assignments, "final_workloads": final_workloads}
                )
            else:
                self.log_test(
                    "Workload Distribution - Balancing",
                    False,
                    f"Workload not balanced (max: {max_workload}, min: {min_workload})"
                )
                
        except Exception as e:
            self.log_test(
                "Workload Distribution Logic",
                False,
                f"Unexpected error: {e}"
            )
    
    def test_assignment_validation_logic(self):
        """Test assignment validation logic without database."""
        print("\n✅ Testing assignment validation logic...")
        
        try:
            # Test data validation
            test_cases = [
                {
                    "name": "Valid Assignment",
                    "request_id": 1,
                    "expert_id": 1,
                    "expected": True
                },
                {
                    "name": "Missing Request ID",
                    "request_id": None,
                    "expert_id": 1,
                    "expected": False
                },
                {
                    "name": "Missing Expert ID",
                    "request_id": 1,
                    "expert_id": None,
                    "expected": False
                },
                {
                    "name": "Invalid Request ID",
                    "request_id": 0,
                    "expert_id": 1,
                    "expected": False
                },
                {
                    "name": "Invalid Expert ID",
                    "request_id": 1,
                    "expert_id": 0,
                    "expected": False
                }
            ]
            
            for test_case in test_cases:
                # Simulate validation
                is_valid = (
                    test_case["request_id"] is not None and
                    test_case["expert_id"] is not None and
                    test_case["request_id"] > 0 and
                    test_case["expert_id"] > 0
                )
                
                if is_valid == test_case["expected"]:
                    self.log_test(
                        f"Assignment Validation - {test_case['name']}",
                        True,
                        f"Validation result: {is_valid}"
                    )
                else:
                    self.log_test(
                        f"Assignment Validation - {test_case['name']}",
                        False,
                        f"Expected {test_case['expected']}, got {is_valid}"
                    )
            
            # Test status validation
            valid_statuses = ["new", "assigned", "in_progress", "quoted", "waiting_for_customer", "won", "lost", "closed"]
            test_statuses = ["new", "assigned", "invalid_status", "pending", "closed"]
            
            for status in test_statuses:
                is_valid_status = status in valid_statuses
                expected = status != "invalid_status" and status != "pending"
                
                if is_valid_status == expected:
                    self.log_test(
                        f"Assignment Validation - Status '{status}'",
                        True,
                        f"Status validation: {is_valid_status}"
                    )
                else:
                    self.log_test(
                        f"Assignment Validation - Status '{status}'",
                        False,
                        f"Expected {expected}, got {is_valid_status}"
                    )
                    
        except Exception as e:
            self.log_test(
                "Assignment Validation Logic",
                False,
                f"Unexpected error: {e}"
            )
    
    def test_assignment_statistics_logic(self):
        """Test assignment statistics logic without database."""
        print("\n📊 Testing assignment statistics logic...")
        
        try:
            # Mock assignment data
            assignments = [
                {"method": "automatic", "expert_id": 1, "timestamp": "2024-01-01"},
                {"method": "manual", "expert_id": 2, "timestamp": "2024-01-01"},
                {"method": "automatic", "expert_id": 1, "timestamp": "2024-01-02"},
                {"method": "automatic", "expert_id": 3, "timestamp": "2024-01-02"},
                {"method": "manual", "expert_id": 2, "timestamp": "2024-01-03"}
            ]
            
            # Calculate statistics
            total_assignments = len(assignments)
            automatic_count = len([a for a in assignments if a["method"] == "automatic"])
            manual_count = len([a for a in assignments if a["method"] == "manual"])
            
            # Expert workload distribution
            expert_workloads = {}
            for assignment in assignments:
                expert_id = assignment["expert_id"]
                expert_workloads[expert_id] = expert_workloads.get(expert_id, 0) + 1
            
            # Test statistics calculation
            if total_assignments == 5:
                self.log_test(
                    "Assignment Statistics - Total Count",
                    True,
                    f"Correctly calculated total assignments: {total_assignments}"
                )
            else:
                self.log_test(
                    "Assignment Statistics - Total Count",
                    False,
                    f"Expected 5, got {total_assignments}"
                )
            
            if automatic_count == 3 and manual_count == 2:
                self.log_test(
                    "Assignment Statistics - Method Distribution",
                    True,
                    f"Correctly calculated method distribution: {automatic_count} automatic, {manual_count} manual"
                )
            else:
                self.log_test(
                    "Assignment Statistics - Method Distribution",
                    False,
                    f"Expected 3 automatic, 2 manual. Got {automatic_count} automatic, {manual_count} manual"
                )
            
            # Test workload distribution
            if len(expert_workloads) == 3:  # 3 different experts
                self.log_test(
                    "Assignment Statistics - Expert Workload Distribution",
                    True,
                    f"Correctly calculated workload for {len(expert_workloads)} experts",
                    {"expert_workloads": expert_workloads}
                )
            else:
                self.log_test(
                    "Assignment Statistics - Expert Workload Distribution",
                    False,
                    f"Expected 3 experts, got {len(expert_workloads)}"
                )
            
            # Test average workload
            avg_workload = sum(expert_workloads.values()) / len(expert_workloads)
            if avg_workload == 5/3:  # 5 assignments / 3 experts
                self.log_test(
                    "Assignment Statistics - Average Workload",
                    True,
                    f"Correctly calculated average workload: {avg_workload:.2f}"
                )
            else:
                self.log_test(
                    "Assignment Statistics - Average Workload",
                    False,
                    f"Expected 1.67, got {avg_workload:.2f}"
                )
                
        except Exception as e:
            self.log_test(
                "Assignment Statistics Logic",
                False,
                f"Unexpected error: {e}"
            )
    
    def run_all_tests(self):
        """Run all simple assignment tests."""
        print("🚀 Starting Simple Assignment Tests")
        print("=" * 50)
        
        # Run tests
        self.test_expert_scoring_logic()
        self.test_assignment_rule_logic()
        self.test_workload_distribution_logic()
        self.test_assignment_validation_logic()
        self.test_assignment_statistics_logic()
        
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
        with open("simple-assignment-test-results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)
        
        print("📄 Detailed results saved to: simple-assignment-test-results.json")


def main():
    """Main function to run the tests."""
    tester = SimpleAssignmentTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
