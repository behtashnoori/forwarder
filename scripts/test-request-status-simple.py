#!/usr/bin/env python3
"""
Simple test script for request status changes.
This script tests the status change logic without requiring complex imports.
"""

import sys
import os
import json
from datetime import datetime, timedelta


class MockShipmentRequest:
    """Mock ShipmentRequest class for testing."""
    
    def __init__(self, request_id, status="new", assigned_to=None, sla_due_at=None):
        self.id = request_id
        self.status = status
        self.assigned_to = assigned_to
        self.sla_due_at = sla_due_at
        self.has_unread_for_assignee = True
        self.last_customer_touch_at = None
        self.priority = "normal"
        self.created_at = datetime.utcnow()


class MockExpertUser:
    """Mock ExpertUser class for testing."""
    
    def __init__(self, user_id, username="test_expert", full_name="کارشناس تست"):
        self.id = user_id
        self.username = username
        self.full_name = full_name
        self.is_active = True


class MockExpertConsoleLog:
    """Mock ExpertConsoleLog class for testing."""
    
    def __init__(self, shipment_request_id, expert_user_id, action, old_status, new_status, note):
        self.shipment_request_id = shipment_request_id
        self.expert_user_id = expert_user_id
        self.action = action
        self.old_status = old_status
        self.new_status = new_status
        self.note = note
        self.created_at = datetime.utcnow()


class MockExpertConsoleNotification:
    """Mock ExpertConsoleNotification class for testing."""
    
    def __init__(self, expert_user_id, shipment_request_id, notification_type, title, message):
        self.expert_user_id = expert_user_id
        self.shipment_request_id = shipment_request_id
        self.notification_type = notification_type
        self.title = title
        self.message = message
        self.is_read = False
        self.created_at = datetime.utcnow()


class TestRequestStatusChanges:
    """Test class for request status change functionality."""
    
    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "test_details": []
        }
        self.logs = []
        self.notifications = []
        
    def run_test(self, test_name, test_func):
        """Run a single test and record results."""
        self.test_results["total_tests"] += 1
        print(f"\n🧪 Running test: {test_name}")
        
        try:
            result = test_func()
            if result:
                self.test_results["passed"] += 1
                print(f"✅ PASSED: {test_name}")
                self.test_results["test_details"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "message": "Test completed successfully"
                })
            else:
                self.test_results["failed"] += 1
                print(f"❌ FAILED: {test_name}")
                self.test_results["test_details"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "message": "Test failed"
                })
        except Exception as e:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {str(e)}")
            print(f"💥 ERROR in {test_name}: {str(e)}")
            self.test_results["test_details"].append({
                "name": test_name,
                "status": "ERROR",
                "message": str(e)
            })
    
    def change_request_status(self, request, new_status, expert_id=None, note=""):
        """Change the status of a request and create appropriate logs."""
        old_status = request.status
        
        # Validate status
        valid_statuses = ["new", "assigned", "in_progress", "quoted", "waiting_for_customer", "won", "lost", "closed"]
        if new_status not in valid_statuses:
            return False, "Invalid status"
        
        # Update request status
        request.status = new_status
        request.has_unread_for_assignee = True
        
        # Set SLA due date for new assignments
        if new_status == "assigned" and not request.sla_due_at:
            request.sla_due_at = datetime.utcnow() + timedelta(hours=2)
        
        # Create log entry
        log = MockExpertConsoleLog(
            shipment_request_id=request.id,
            expert_user_id=expert_id or request.assigned_to,
            action="status_change",
            old_status=old_status,
            new_status=new_status,
            note=note
        )
        self.logs.append(log)
        
        # Create notification if assigned
        if request.assigned_to:
            notification = MockExpertConsoleNotification(
                expert_user_id=request.assigned_to,
                shipment_request_id=request.id,
                notification_type="status_change",
                title="تغییر وضعیت درخواست",
                message=f"وضعیت درخواست {request.id} به {new_status} تغییر یافت"
            )
            self.notifications.append(notification)
        
        return True, "Success"
    
    def calculate_sla_status(self, request):
        """Calculate SLA status for a request."""
        if not request.sla_due_at:
            return "no_sla"
        
        current_time = datetime.utcnow()
        
        if current_time > request.sla_due_at:
            return "overdue"
        elif current_time + timedelta(hours=2) > request.sla_due_at:
            return "due_soon"
        else:
            return "on_time"
    
    def test_status_change_new_to_assigned(self):
        """Test changing status from new to assigned."""
        request = MockShipmentRequest(1, "new")
        expert = MockExpertUser(1)
        
        success, message = self.change_request_status(
            request, "assigned", expert.id, "ارجاع به کارشناس"
        )
        
        # Verify changes
        assert success, f"Status change should succeed: {message}"
        assert request.status == "assigned", "Status should be assigned"
        assert request.assigned_to is None, "Should not have assigned_to initially"
        assert request.sla_due_at is not None, "SLA due date should be set"
        assert request.has_unread_for_assignee, "Should have unread flag"
        
        # Check log entry
        assert len(self.logs) == 1, "Log entry should be created"
        log = self.logs[0]
        assert log.action == "status_change", "Log action should be status_change"
        assert log.old_status == "new", "Old status should be new"
        assert log.new_status == "assigned", "New status should be assigned"
        
        return True
    
    def test_status_change_assigned_to_in_progress(self):
        """Test changing status from assigned to in_progress."""
        request = MockShipmentRequest(2, "assigned", assigned_to=1)
        expert = MockExpertUser(1)
        
        success, message = self.change_request_status(
            request, "in_progress", expert.id, "شروع کار روی درخواست"
        )
        
        # Verify changes
        assert success, f"Status change should succeed: {message}"
        assert request.status == "in_progress", "Status should be in_progress"
        assert request.has_unread_for_assignee, "Should have unread flag"
        
        # Check log entry
        log = self.logs[-1]  # Get the last log entry
        assert log.old_status == "assigned", "Old status should be assigned"
        assert log.new_status == "in_progress", "New status should be in_progress"
        
        return True
    
    def test_status_change_in_progress_to_quoted(self):
        """Test changing status from in_progress to quoted."""
        request = MockShipmentRequest(3, "in_progress", assigned_to=1)
        
        success, message = self.change_request_status(
            request, "quoted", 1, "ارسال پیشنهاد قیمت به مشتری"
        )
        
        # Verify changes
        assert success, f"Status change should succeed: {message}"
        assert request.status == "quoted", "Status should be quoted"
        
        # Check log entry
        log = self.logs[-1]
        assert log.old_status == "in_progress", "Old status should be in_progress"
        assert log.new_status == "quoted", "New status should be quoted"
        
        return True
    
    def test_status_change_quoted_to_waiting_for_customer(self):
        """Test changing status from quoted to waiting_for_customer."""
        request = MockShipmentRequest(4, "quoted", assigned_to=1)
        
        success, message = self.change_request_status(
            request, "waiting_for_customer", 1, "انتظار پاسخ مشتری"
        )
        
        # Verify changes
        assert success, f"Status change should succeed: {message}"
        assert request.status == "waiting_for_customer", "Status should be waiting_for_customer"
        
        # Check log entry
        log = self.logs[-1]
        assert log.old_status == "quoted", "Old status should be quoted"
        assert log.new_status == "waiting_for_customer", "New status should be waiting_for_customer"
        
        return True
    
    def test_status_change_to_won(self):
        """Test changing status to won (successful completion)."""
        request = MockShipmentRequest(5, "waiting_for_customer", assigned_to=1)
        
        success, message = self.change_request_status(
            request, "won", 1, "درخواست با موفقیت تکمیل شد"
        )
        
        # Verify changes
        assert success, f"Status change should succeed: {message}"
        assert request.status == "won", "Status should be won"
        assert request.has_unread_for_assignee, "Should have unread flag"
        
        # Check log entry
        log = self.logs[-1]
        assert log.old_status == "waiting_for_customer", "Old status should be waiting_for_customer"
        assert log.new_status == "won", "New status should be won"
        
        return True
    
    def test_status_change_to_lost(self):
        """Test changing status to lost (unsuccessful completion)."""
        request = MockShipmentRequest(6, "waiting_for_customer", assigned_to=1)
        
        success, message = self.change_request_status(
            request, "lost", 1, "درخواست منتفی شد"
        )
        
        # Verify changes
        assert success, f"Status change should succeed: {message}"
        assert request.status == "lost", "Status should be lost"
        assert request.has_unread_for_assignee, "Should have unread flag"
        
        # Check log entry
        log = self.logs[-1]
        assert log.old_status == "waiting_for_customer", "Old status should be waiting_for_customer"
        assert log.new_status == "lost", "New status should be lost"
        
        return True
    
    def test_status_change_to_closed(self):
        """Test changing status to closed."""
        request = MockShipmentRequest(7, "won", assigned_to=1)
        
        success, message = self.change_request_status(
            request, "closed", 1, "درخواست بسته شد"
        )
        
        # Verify changes
        assert success, f"Status change should succeed: {message}"
        assert request.status == "closed", "Status should be closed"
        assert request.has_unread_for_assignee, "Should have unread flag"
        
        # Check log entry
        log = self.logs[-1]
        assert log.old_status == "won", "Old status should be won"
        assert log.new_status == "closed", "New status should be closed"
        
        return True
    
    def test_invalid_status_change(self):
        """Test changing to an invalid status."""
        request = MockShipmentRequest(8, "new")
        
        success, message = self.change_request_status(
            request, "invalid_status", 1, "Invalid status test"
        )
        
        # Verify that invalid status is rejected
        assert not success, "Invalid status should be rejected"
        assert request.status == "new", "Original status should be preserved"
        
        return True
    
    def test_sla_compliance_assigned_status(self):
        """Test SLA compliance when status changes to assigned."""
        request = MockShipmentRequest(9, "new")
        
        # Change to assigned status
        success, message = self.change_request_status(
            request, "assigned", 1, "ارجاع به کارشناس"
        )
        
        # Verify SLA is set
        assert success, f"Status change should succeed: {message}"
        assert request.sla_due_at is not None, "SLA due date should be set"
        
        # Check SLA status
        sla_status = self.calculate_sla_status(request)
        assert sla_status == "on_time", "SLA should be on time for new assignment"
        
        return True
    
    def test_sla_compliance_overdue_status(self):
        """Test SLA compliance for overdue requests."""
        # Create request with overdue SLA
        overdue_time = datetime.utcnow() - timedelta(hours=1)
        request = MockShipmentRequest(10, "assigned", assigned_to=1, sla_due_at=overdue_time)
        
        # Check SLA status
        sla_status = self.calculate_sla_status(request)
        assert sla_status == "overdue", "SLA should be overdue"
        
        return True
    
    def test_sla_compliance_due_soon_status(self):
        """Test SLA compliance for requests due soon."""
        # Create request with SLA due soon (within 2 hours)
        due_soon_time = datetime.utcnow() + timedelta(hours=1)
        request = MockShipmentRequest(11, "assigned", assigned_to=1, sla_due_at=due_soon_time)
        
        # Check SLA status
        sla_status = self.calculate_sla_status(request)
        assert sla_status == "due_soon", "SLA should be due soon"
        
        return True
    
    def test_multiple_status_transitions(self):
        """Test multiple status transitions in sequence."""
        request = MockShipmentRequest(12, "new")
        
        # Test sequence: new -> assigned -> in_progress -> quoted -> waiting_for_customer -> won
        transitions = [
            ("assigned", "ارجاع به کارشناس"),
            ("in_progress", "شروع کار"),
            ("quoted", "ارسال پیشنهاد قیمت"),
            ("waiting_for_customer", "انتظار پاسخ مشتری"),
            ("won", "تکمیل موفق")
        ]
        
        for new_status, note in transitions:
            success, message = self.change_request_status(
                request, new_status, 1, note
            )
            assert success, f"Status change to {new_status} should succeed: {message}"
            assert request.status == new_status, f"Status should be {new_status}"
        
        # Verify final status
        assert request.status == "won", "Final status should be won"
        
        # Verify all log entries were created
        assert len(self.logs) >= len(transitions), "All log entries should be created"
        
        return True
    
    def run_all_tests(self):
        """Run all tests."""
        print("🚀 Starting Request Status Change Tests")
        print("=" * 50)
        
        # Define all tests
        tests = [
            ("Status Change: New to Assigned", self.test_status_change_new_to_assigned),
            ("Status Change: Assigned to In Progress", self.test_status_change_assigned_to_in_progress),
            ("Status Change: In Progress to Quoted", self.test_status_change_in_progress_to_quoted),
            ("Status Change: Quoted to Waiting for Customer", self.test_status_change_quoted_to_waiting_for_customer),
            ("Status Change: To Won", self.test_status_change_to_won),
            ("Status Change: To Lost", self.test_status_change_to_lost),
            ("Status Change: To Closed", self.test_status_change_to_closed),
            ("Invalid Status Change", self.test_invalid_status_change),
            ("SLA Compliance: Assigned Status", self.test_sla_compliance_assigned_status),
            ("SLA Compliance: Overdue Status", self.test_sla_compliance_overdue_status),
            ("SLA Compliance: Due Soon Status", self.test_sla_compliance_due_soon_status),
            ("Multiple Status Transitions", self.test_multiple_status_transitions),
        ]
        
        # Run each test
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print summary
        self.print_test_summary()
        
        return self.test_results
    
    def print_test_summary(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {self.test_results['total_tests']}")
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"Success Rate: {(self.test_results['passed'] / self.test_results['total_tests'] * 100):.1f}%")
        
        if self.test_results['errors']:
            print(f"\n💥 Errors:")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        
        print("\n📋 Detailed Results:")
        for test in self.test_results['test_details']:
            status_icon = "✅" if test['status'] == "PASSED" else "❌"
            print(f"  {status_icon} {test['name']}: {test['status']}")
            if test['status'] != "PASSED":
                print(f"    Message: {test['message']}")


def main():
    """Main function to run tests."""
    print("🧪 Request Status Change Test Suite")
    print("Testing expert console request status change functionality")
    print("=" * 60)
    
    # Initialize test runner
    test_runner = TestRequestStatusChanges()
    
    # Run all tests
    results = test_runner.run_all_tests()
    
    # Save results to file
    results_file = "request-status-change-simple-test-results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Test results saved to: {results_file}")
    
    # Exit with appropriate code
    if results['failed'] > 0:
        print(f"\n❌ Tests failed. Exiting with code 1.")
        sys.exit(1)
    else:
        print(f"\n✅ All tests passed! Exiting with code 0.")
        sys.exit(0)


if __name__ == "__main__":
    main()
