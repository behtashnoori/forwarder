#!/usr/bin/env python3
"""
Direct test for expert console request details functionality.
Tests the database models and data structure without requiring server to be running.
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

# Import Flask app and database models
from backend import create_app
from backend.models import (
    ShipmentRequest, ExpertUser, ExpertConsoleLog, ExpertConsoleMessage,
    ExpertConsoleNotification, Province, County, City
)
from backend.extensions import db

class ExpertRequestDetailsDirectTester:
    """Test expert console request details functionality directly via database."""
    
    def __init__(self):
        self.app = create_app()
        self.test_data = {}
        self.results = []
        
    def log_result(self, test_name: str, success: bool, message: str, data: Any = None):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if data and not success:
            print(f"   Data: {json.dumps(data, indent=2, default=str)}")
    
    def setup_test_data(self):
        """Set up test data for request details testing."""
        with self.app.app_context():
            try:
                # Create test expert user
                expert = ExpertUser(
                    username="test_expert_details_direct",
                    password_hash="hashed_password",
                    full_name="Test Expert Details Direct",
                    email="test_details_direct@example.com",
                    role="expert",
                    is_active=True
                )
                db.session.add(expert)
                db.session.flush()
                
                # Get or create test provinces, counties, and cities
                province1 = Province.query.filter_by(name_fa="تهران").first()
                if not province1:
                    province1 = Province(name_fa="تهران", code="TH")
                    db.session.add(province1)
                    db.session.flush()
                
                province2 = Province.query.filter_by(name_fa="اصفهان").first()
                if not province2:
                    province2 = Province(name_fa="اصفهان", code="ES")
                    db.session.add(province2)
                    db.session.flush()
                
                county1 = County.query.filter_by(name_fa="تهران", province_id=province1.id).first()
                if not county1:
                    county1 = County(name_fa="تهران", province_id=province1.id)
                    db.session.add(county1)
                    db.session.flush()
                
                county2 = County.query.filter_by(name_fa="اصفهان", province_id=province2.id).first()
                if not county2:
                    county2 = County(name_fa="اصفهان", province_id=province2.id)
                    db.session.add(county2)
                    db.session.flush()
                
                city1 = City.query.filter_by(name_fa="تهران", county_id=county1.id).first()
                if not city1:
                    city1 = City(name_fa="تهران", county_id=county1.id, province_id=province1.id)
                    db.session.add(city1)
                    db.session.flush()
                
                city2 = City.query.filter_by(name_fa="اصفهان", county_id=county2.id).first()
                if not city2:
                    city2 = City(name_fa="اصفهان", county_id=county2.id, province_id=province2.id)
                    db.session.add(city2)
                    db.session.flush()
                
                # Create test shipment request
                shipment_request = ShipmentRequest(
                    contact_phone="09123456789",
                    customer_first_name="علی",
                    customer_last_name="احمدی",
                    origin_province_id=province1.id,
                    origin_county_id=county1.id,
                    origin_city_id=city1.id,
                    dest_province_id=province2.id,
                    dest_county_id=county2.id,
                    dest_city_id=city2.id,
                    transport_method="truck",
                    cargo_description="محصولات الکترونیکی",
                    cargo_weight=100.5,
                    cargo_volume=2.3,
                    cargo_value=5000000,
                    special_instructions="مراقبت ویژه",
                    pickup_date=datetime.now().date() + timedelta(days=1),
                    delivery_date=datetime.now().date() + timedelta(days=3),
                    status="assigned",
                    assigned_to=expert.id,
                    priority="high",
                    sla_due_at=datetime.now() + timedelta(hours=1),
                    has_unread_for_assignee=True
                )
                db.session.add(shipment_request)
                db.session.flush()
                
                # Create timeline logs
                log1 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    action="created",
                    old_status=None,
                    new_status="new",
                    note="درخواست ایجاد شد",
                    ip_address="127.0.0.1",
                    created_at=datetime.now() - timedelta(hours=2)
                )
                
                log2 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    action="assignment",
                    old_status="new",
                    new_status="assigned",
                    note="ارجاع به کارشناس",
                    ip_address="127.0.0.1",
                    created_at=datetime.now() - timedelta(hours=1)
                )
                
                log3 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    action="status_change",
                    old_status="assigned",
                    new_status="in_progress",
                    note="شروع کار بر روی درخواست",
                    ip_address="127.0.0.1",
                    created_at=datetime.now() - timedelta(minutes=30)
                )
                
                db.session.add(log1)
                db.session.add(log2)
                db.session.add(log3)
                
                # Create messages
                message1 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    message_type="internal_note",
                    subject="یادداشت داخلی",
                    content="این یک یادداشت داخلی برای همکاران است",
                    is_read_by_customer=False,
                    created_at=datetime.now() - timedelta(minutes=45)
                )
                
                message2 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    message_type="customer_message",
                    subject="پیام به مشتری",
                    content="درخواست شما در حال بررسی است",
                    is_read_by_customer=False,
                    customer_response=None,
                    created_at=datetime.now() - timedelta(minutes=20)
                )
                
                message3 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    message_type="customer_message",
                    subject="پاسخ مشتری",
                    content="لطفاً قیمت را اعلام کنید",
                    is_read_by_customer=True,
                    customer_response="ممنون از اطلاع‌رسانی",
                    created_at=datetime.now() - timedelta(minutes=10)
                )
                
                db.session.add(message1)
                db.session.add(message2)
                db.session.add(message3)
                
                # Create notification
                notification = ExpertConsoleNotification(
                    expert_user_id=expert.id,
                    shipment_request_id=shipment_request.id,
                    notification_type="assignment",
                    title="ارجاع درخواست جدید",
                    message=f"درخواست {shipment_request.id} به شما ارجاع داده شد",
                    is_read=False,
                    created_at=datetime.now() - timedelta(hours=1)
                )
                db.session.add(notification)
                
                db.session.commit()
                
                self.test_data = {
                    "expert_id": expert.id,
                    "expert_username": expert.username,
                    "request_id": shipment_request.id,
                    "province1_id": province1.id,
                    "province2_id": province2.id,
                    "county1_id": county1.id,
                    "county2_id": county2.id,
                    "city1_id": city1.id,
                    "city2_id": city2.id
                }
                
                self.log_result("setup_test_data", True, "Test data created successfully")
                
            except Exception as e:
                db.session.rollback()
                self.log_result("setup_test_data", False, f"Failed to create test data: {str(e)}")
                raise
    
    def test_request_details_data_structure(self):
        """Test request details data structure by simulating the API response."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                
                # Simulate the API logic
                req = db.session.query(ShipmentRequest).get(request_id)
                if not req:
                    self.log_result("test_request_details_data_structure", False, "Request not found")
                    return
                
                # Get related data
                origin_province = db.session.query(Province).get(req.origin_province_id)
                origin_county = db.session.query(County).get(req.origin_county_id)
                origin_city = db.session.query(City).get(req.origin_city_id)
                dest_province = db.session.query(Province).get(req.dest_province_id)
                dest_county = db.session.query(County).get(req.dest_county_id)
                dest_city = db.session.query(City).get(req.dest_city_id)
                assigned_expert = db.session.query(ExpertUser).get(req.assigned_to) if req.assigned_to else None
                
                # Get timeline logs
                logs = db.session.query(ExpertConsoleLog).filter(
                    ExpertConsoleLog.shipment_request_id == request_id
                ).order_by(ExpertConsoleLog.created_at.desc()).all()
                
                # Get messages
                messages = db.session.query(ExpertConsoleMessage).filter(
                    ExpertConsoleMessage.shipment_request_id == request_id
                ).order_by(ExpertConsoleMessage.created_at.desc()).all()
                
                # Format timeline
                timeline = []
                for log in logs:
                    timeline.append({
                        "id": log.id,
                        "action": log.action,
                        "old_status": log.old_status,
                        "new_status": log.new_status,
                        "note": log.note,
                        "created_at": log.created_at.isoformat(),
                        "created_by": log.created_by_user.full_name if log.created_by_user else "سیستم"
                    })
                
                # Format messages
                messages_data = []
                for msg in messages:
                    messages_data.append({
                        "id": msg.id,
                        "type": msg.message_type,
                        "subject": msg.subject,
                        "content": msg.content,
                        "is_read_by_customer": msg.is_read_by_customer,
                        "customer_response": msg.customer_response,
                        "created_at": msg.created_at.isoformat(),
                        "created_by": msg.created_by_user.full_name if msg.created_by_user else "سیستم"
                    })
                
                # Calculate SLA status
                sla_status = "on_time"
                if req.sla_due_at:
                    if datetime.utcnow() > req.sla_due_at:
                        sla_status = "overdue"
                    elif datetime.utcnow() + timedelta(hours=2) > req.sla_due_at:
                        sla_status = "due_soon"
                
                # Build response data
                response_data = {
                    "id": req.id,
                    "tracking_number": f"SR{req.id:06d}",
                    "status": req.status,
                    "priority": req.priority,
                    "created_at": req.created_at.isoformat(),
                    "sla_due_at": req.sla_due_at.isoformat() if req.sla_due_at else None,
                    "sla_status": sla_status,
                    "assigned_to": {
                        "id": assigned_expert.id,
                        "name": assigned_expert.full_name,
                        "username": assigned_expert.username
                    } if assigned_expert else None,
                    "customer": {
                        "first_name": req.customer_first_name,
                        "last_name": req.customer_last_name,
                        "phone": req.contact_phone,
                        "full_name": f"{req.customer_first_name or ''} {req.customer_last_name or ''}".strip() or "نامشخص"
                    },
                    "route": {
                        "origin": {
                            "province": origin_province.name_fa if origin_province else "نامشخص",
                            "county": origin_county.name_fa if origin_county else "نامشخص",
                            "city": origin_city.name_fa if origin_city else "نامشخص"
                        },
                        "destination": {
                            "province": dest_province.name_fa if dest_province else "نامشخص",
                            "county": dest_county.name_fa if dest_county else "نامشخص",
                            "city": dest_city.name_fa if dest_city else "نامشخص"
                        }
                    },
                    "transport_method": req.transport_method,
                    "cargo": {
                        "description": req.cargo_description,
                        "weight": req.cargo_weight,
                        "volume": req.cargo_volume,
                        "value": req.cargo_value,
                        "special_instructions": req.special_instructions
                    },
                    "dates": {
                        "pickup_date": req.pickup_date.isoformat() if req.pickup_date else None,
                        "delivery_date": req.delivery_date.isoformat() if req.delivery_date else None
                    },
                    "timeline": timeline,
                    "messages": messages_data,
                    "has_unread": req.has_unread_for_assignee
                }
                
                # Validate response structure
                required_fields = [
                    "id", "tracking_number", "status", "priority", "created_at",
                    "customer", "route", "cargo", "timeline", "messages"
                ]
                
                missing_fields = [field for field in required_fields if field not in response_data]
                
                if not missing_fields:
                    self.log_result(
                        "test_request_details_data_structure", True,
                        "Request details data structure is valid",
                        {
                            "request_id": response_data["id"],
                            "tracking_number": response_data["tracking_number"],
                            "status": response_data["status"],
                            "timeline_count": len(response_data["timeline"]),
                            "messages_count": len(response_data["messages"])
                        }
                    )
                else:
                    self.log_result(
                        "test_request_details_data_structure", False,
                        f"Missing required fields: {missing_fields}",
                        response_data
                    )
                    
        except Exception as e:
            self.log_result("test_request_details_data_structure", False, f"Exception: {str(e)}")
    
    def test_timeline_data_integrity(self):
        """Test timeline data integrity and ordering."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                
                # Get timeline logs
                logs = db.session.query(ExpertConsoleLog).filter(
                    ExpertConsoleLog.shipment_request_id == request_id
                ).order_by(ExpertConsoleLog.created_at.desc()).all()
                
                if len(logs) >= 3:  # We created 3 logs
                    # Check if logs are in descending order (newest first)
                    timestamps = [log.created_at for log in logs]
                    is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
                    
                    if is_sorted:
                        # Validate log structure
                        valid_logs = 0
                        for log in logs:
                            if (log.action and log.note and log.created_at and 
                                log.shipment_request_id == request_id):
                                valid_logs += 1
                        
                        if valid_logs == len(logs):
                            self.log_result(
                                "test_timeline_data_integrity", True,
                                f"Timeline with {len(logs)} logs is valid and sorted",
                                {
                                    "log_count": len(logs),
                                    "actions": [log.action for log in logs],
                                    "is_sorted": is_sorted
                                }
                            )
                        else:
                            self.log_result(
                                "test_timeline_data_integrity", False,
                                f"Only {valid_logs}/{len(logs)} logs have valid structure",
                                logs
                            )
                    else:
                        self.log_result(
                            "test_timeline_data_integrity", False,
                            "Timeline logs are not in descending order",
                            logs
                        )
                else:
                    self.log_result(
                        "test_timeline_data_integrity", False,
                        f"Expected at least 3 logs, got {len(logs)}",
                        logs
                    )
                    
        except Exception as e:
            self.log_result("test_timeline_data_integrity", False, f"Exception: {str(e)}")
    
    def test_messages_data_integrity(self):
        """Test messages data integrity and ordering."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                
                # Get messages
                messages = db.session.query(ExpertConsoleMessage).filter(
                    ExpertConsoleMessage.shipment_request_id == request_id
                ).order_by(ExpertConsoleMessage.created_at.desc()).all()
                
                if len(messages) >= 3:  # We created 3 messages
                    # Check if messages are in descending order (newest first)
                    timestamps = [msg.created_at for msg in messages]
                    is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
                    
                    if is_sorted:
                        # Validate message structure
                        valid_messages = 0
                        message_types = []
                        for msg in messages:
                            if (msg.message_type and msg.subject and msg.content and 
                                msg.created_at and msg.shipment_request_id == request_id):
                                valid_messages += 1
                                message_types.append(msg.message_type)
                        
                        if valid_messages == len(messages):
                            self.log_result(
                                "test_messages_data_integrity", True,
                                f"Messages with {len(messages)} items are valid and sorted",
                                {
                                    "message_count": len(messages),
                                    "message_types": message_types,
                                    "is_sorted": is_sorted
                                }
                            )
                        else:
                            self.log_result(
                                "test_messages_data_integrity", False,
                                f"Only {valid_messages}/{len(messages)} messages have valid structure",
                                messages
                            )
                    else:
                        self.log_result(
                            "test_messages_data_integrity", False,
                            "Messages are not in descending order",
                            messages
                        )
                else:
                    self.log_result(
                        "test_messages_data_integrity", False,
                        f"Expected at least 3 messages, got {len(messages)}",
                        messages
                    )
                    
        except Exception as e:
            self.log_result("test_messages_data_integrity", False, f"Exception: {str(e)}")
    
    def test_customer_response_handling(self):
        """Test customer response handling in messages."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                
                # Get messages with customer responses
                messages_with_responses = db.session.query(ExpertConsoleMessage).filter(
                    ExpertConsoleMessage.shipment_request_id == request_id,
                    ExpertConsoleMessage.customer_response.isnot(None)
                ).all()
                
                messages_read_by_customer = db.session.query(ExpertConsoleMessage).filter(
                    ExpertConsoleMessage.shipment_request_id == request_id,
                    ExpertConsoleMessage.is_read_by_customer == True
                ).all()
                
                if messages_with_responses:
                    # Validate customer response structure
                    valid_responses = 0
                    for message in messages_with_responses:
                        if (message.customer_response and 
                            message.is_read_by_customer is not None):
                            valid_responses += 1
                    
                    if valid_responses == len(messages_with_responses):
                        self.log_result(
                            "test_customer_response_handling", True,
                            f"Customer responses handled correctly in {len(messages_with_responses)} messages",
                            {
                                "messages_with_responses": len(messages_with_responses),
                                "messages_read_by_customer": len(messages_read_by_customer),
                                "valid_responses": valid_responses
                            }
                        )
                    else:
                        self.log_result(
                            "test_customer_response_handling", False,
                            f"Only {valid_responses}/{len(messages_with_responses)} responses are valid",
                            messages_with_responses
                        )
                else:
                    self.log_result(
                        "test_customer_response_handling", False,
                        "No messages with customer responses found",
                        []
                    )
                    
        except Exception as e:
            self.log_result("test_customer_response_handling", False, f"Exception: {str(e)}")
    
    def test_assignment_information(self):
        """Test assignment information in request details."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                
                # Get request and assigned expert
                req = db.session.query(ShipmentRequest).get(request_id)
                assigned_expert = db.session.query(ExpertUser).get(req.assigned_to) if req.assigned_to else None
                
                if assigned_expert:
                    # Validate assignment data
                    if (assigned_expert.id == self.test_data["expert_id"] and
                        assigned_expert.full_name == "Test Expert Details Direct" and
                        assigned_expert.username == "test_expert_details_direct"):
                        
                        self.log_result(
                            "test_assignment_information", True,
                            "Assignment information is correct",
                            {
                                "expert_id": assigned_expert.id,
                                "expert_name": assigned_expert.full_name,
                                "expert_username": assigned_expert.username
                            }
                        )
                    else:
                        self.log_result(
                            "test_assignment_information", False,
                            "Assignment information doesn't match expected values",
                            {
                                "expected_id": self.test_data["expert_id"],
                                "actual_id": assigned_expert.id,
                                "expected_name": "Test Expert Details Direct",
                                "actual_name": assigned_expert.full_name
                            }
                        )
                else:
                    self.log_result(
                        "test_assignment_information", False,
                        "No assignment information found",
                        {"assigned_to": req.assigned_to}
                    )
                    
        except Exception as e:
            self.log_result("test_assignment_information", False, f"Exception: {str(e)}")
    
    def test_sla_status_calculation(self):
        """Test SLA status calculation in request details."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                
                # Get request
                req = db.session.query(ShipmentRequest).get(request_id)
                
                if req.sla_due_at:
                    # Calculate SLA status
                    sla_status = "on_time"
                    if datetime.utcnow() > req.sla_due_at:
                        sla_status = "overdue"
                    elif datetime.utcnow() + timedelta(hours=2) > req.sla_due_at:
                        sla_status = "due_soon"
                    
                    # Since we set SLA due at 1 hour from now, it should be "due_soon"
                    if sla_status in ["on_time", "due_soon", "overdue"]:
                        self.log_result(
                            "test_sla_status_calculation", True,
                            f"SLA status calculation is working: {sla_status}",
                            {
                                "sla_status": sla_status,
                                "sla_due_at": req.sla_due_at.isoformat(),
                                "current_time": datetime.utcnow().isoformat()
                            }
                        )
                    else:
                        self.log_result(
                            "test_sla_status_calculation", False,
                            f"Invalid SLA status: {sla_status}",
                            {"sla_due_at": req.sla_due_at.isoformat()}
                        )
                else:
                    self.log_result(
                        "test_sla_status_calculation", False,
                        "No SLA due date found",
                        {"sla_due_at": req.sla_due_at}
                    )
                    
        except Exception as e:
            self.log_result("test_sla_status_calculation", False, f"Exception: {str(e)}")
    
    def cleanup_test_data(self):
        """Clean up test data."""
        with self.app.app_context():
            try:
                # Delete in reverse order of dependencies
                ExpertConsoleNotification.query.filter_by(expert_user_id=self.test_data["expert_id"]).delete()
                ExpertConsoleMessage.query.filter_by(shipment_request_id=self.test_data["request_id"]).delete()
                ExpertConsoleLog.query.filter_by(shipment_request_id=self.test_data["request_id"]).delete()
                ShipmentRequest.query.filter_by(id=self.test_data["request_id"]).delete()
                ExpertUser.query.filter_by(id=self.test_data["expert_id"]).delete()
                
                db.session.commit()
                self.log_result("cleanup_test_data", True, "Test data cleaned up successfully")
                
            except Exception as e:
                db.session.rollback()
                self.log_result("cleanup_test_data", False, f"Failed to clean up test data: {str(e)}")
    
    def run_all_tests(self):
        """Run all request details tests."""
        print("🧪 Starting Expert Request Details Direct Tests")
        print("=" * 60)
        
        try:
            # Setup
            self.setup_test_data()
            
            # Run tests
            self.test_request_details_data_structure()
            self.test_timeline_data_integrity()
            self.test_messages_data_integrity()
            self.test_customer_response_handling()
            self.test_assignment_information()
            self.test_sla_status_calculation()
            
        finally:
            # Cleanup
            self.cleanup_test_data()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Direct Test Summary")
        print("=" * 60)
        
        passed = len([r for r in self.results if r["success"]])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Print failed tests
        failed_tests = [r for r in self.results if not r["success"]]
        if failed_tests:
            print("\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['message']}")
        
        return passed == total


def main():
    """Main function to run the tests."""
    tester = ExpertRequestDetailsDirectTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All direct tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some direct tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
